"""Upload de arquivo FIT (issue #95, ADR 0006, itens 4 e 5)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.db.models import Atividade, Atleta, CheckinTreino
from app.db.session import get_session
from app.ingestao.fit_guardado import AtletaInexistente
from app.ingestao.importacao import (
    TAMANHO_MAX_FIT,
    FitGrande,
    FitInvalido,
    FitNaoEAtividade,
    importar_fit,
)
from app.metricas import esforcos as ef
from app.metricas.tiros_1km import formatar_pace
from app.rotas.checkin import CheckinOut, checkin_out
from app.rotas.evolucao import Erro
from app.rotas.transicao import TransicaoOut, transicao_da_atividade
from app.servicos import checkin as checkin_svc
from app.servicos.carga_leitura import CargaLida, carga_da_atividade
from app.servicos.carga_pse_leitura import CargaPseLida, carga_pse_da_atividade
from app.servicos.clima import ClimaDaAtividade, EstadoClima, clima_da_atividade
from app.servicos.distancia_texto import distancia_da_atividade
from app.servicos.esforcos_leitura import esforcos_da_atividade
from app.servicos.feedback_leitura import FeedbackLido, feedback_da_atividade
from app.servicos.recuperacao_pacote import carregar_da_atividade, importado_em_de_hoje
from app.servicos.fuso import inicio_local
from app.servicos.linha_base_leitura import linha_base_da_atividade, texto_divergencia

router = APIRouter(prefix="/atletas/{atleta_id}/atividades", tags=["atividades"])

PEDACO = 64 * 1024


class UploadFitOut(BaseModel):
    resultado: Literal["inserida", "atualizada", "ignorada"]
    atividade_id: int
    avisos: list[str]


class ClimaOut(BaseModel):
    """Clima da atividade (ADR 0007, item 5). Os quatro valores so existem em `ok`; nos outros estados nem aparecem."""

    estado: EstadoClima
    temperatura_c: float | None = Field(None, exclude_if=lambda v: v is None)
    sensacao_c: float | None = Field(None, exclude_if=lambda v: v is None)
    umidade_pct: float | None = Field(None, exclude_if=lambda v: v is None)
    vento_kmh: float | None = Field(None, exclude_if=lambda v: v is None)
    atribuicao: str | None = Field(None, exclude_if=lambda v: v is None)  # so em `ok` (ADR 0007, item 4)


class BlocoOut(BaseModel):
    """Um bloco do treino (ADR 0008). Textos prontos para a tela; os numeros seguem para quem precisar (1 casa)."""

    ordem: int
    categoria: Literal["esforco", "recuperacao", "aquecimento", "desaquecimento", "leve"]
    faixa: str | None  # d400, t4...; null fora de qualquer faixa (e nos que nao sao esforco)
    faixa_rotulo: str | None  # "400 m", "4 min"
    treino_chave: bool
    inicio_offset_s: float
    duracao_s: float
    distancia_m: float | None
    parada_apos_s: float | None
    fc_media: float | None
    pace_s_km: float | None = Field(None, exclude_if=lambda v: v is None)  # so corrida
    velocidade_kmh: float | None = Field(None, exclude_if=lambda v: v is None)  # so ciclismo
    duracao: str  # m:ss (minutos sem limite)
    distancia: str | None  # "400 m" ou "1,50 km"
    pace: str | None = Field(None, exclude_if=lambda v: v is None)  # m:ss por km; so corrida
    velocidade: str | None = Field(None, exclude_if=lambda v: v is None)  # "25,3 km/h"; so ciclismo
    parada_apos: str | None  # m:ss; null quando nao ha parada depois do bloco


class EsforcosOut(BaseModel):
    """Blocos e esforcos que o comando `detectar_esforcos` gravou (#166). A leitura nao detecta."""

    versao: str  # esforcos@1
    referencia_da_atividade: bool  # true: sem historico, a referencia foi a da propria atividade (a tela avisa)
    treino_chave: bool  # algum esforco faz parte de um treino-chave continuo
    blocos: list[BlocoOut]  # em ordem; vazio se nao ha blocos


class CargaAtividadeOut(BaseModel):
    """Carga de treino da atividade (ADR 0010, item 7). So carga, metodo, motivo e cobertura: nunca limiar nem zonas."""

    estado: Literal["calculada", "sem_carga", "pendente"]  # pendente: o comando calcular_carga ainda nao rodou (ou a versao mudou)
    carga: float | None = None  # so em `calculada`; sem arredondar
    metodo: Literal["rtss", "hrtss"] | None = None  # so em `calculada`
    cobertura_pct: float | None = None  # % da duracao com dado, do metodo usado; pode vir em `cobertura_insuficiente`
    motivo: Literal[
        "sem_dados_saude", "sem_limiar_na_data", "sem_fc", "sem_pace", "cobertura_insuficiente", "modalidade_sem_carga"
    ] | None = None  # so em `sem_carga`
    versao: str | None = None  # carga@2; null em `pendente`


class DivergenciaOut(BaseModel):
    """O formato do treino contradiz o plano da semana-padrao (ADR 0011, item 4). So dado: o tipo do plano nao muda."""

    motivo: Literal["sem_esforco", "tem_tiros"]
    texto: str  # pronto, ex.: "O plano diz intervalado, mas o treino nao teve esforco detectado."


class MetricaBaseOut(BaseModel):
    """Uma metrica da linha de base. Os numeros brutos (`valor`, `mediana`, `desvio`, `z`) saem sem arredondar, para o app ordenar
    e para o motor de explicacao; o texto e so da API. Em `aprendendo` e `sem_valor` nao ha mediana, desvio nem z."""

    chave: Literal["pace_medio", "melhor_pace", "fc_media", "fc_melhor_tiro", "carga_hora"]
    rotulo: str
    unidade: Literal["s/km", "bpm", "pontos/h"]
    estado: Literal["fora", "dentro", "aprendendo", "sem_valor"]
    motivo: str | None = None  # so em `sem_valor`: esteira, sem_tiros, sem_fc, carga_pendente, ...
    valor: float | None = None
    valor_texto: str | None = None
    mediana: float | None = None
    mediana_texto: str | None = None
    desvio: float | None = None
    z: float | None = None
    n: int  # treinos da janela que tem a metrica
    diferenca_texto: str | None = None  # so em `fora`
    texto: str


class LinhaBaseOut(BaseModel):
    """Linha de base da atividade contra o proprio historico, so no mesmo tipo de treino (`linha_base@2`, ADR 0011).
    Calculada na leitura. Compara com o historico do atleta; nao diz se o treino foi bom ou ruim."""

    versao: str
    estado: Literal["ok", "sem_linha_base"]
    motivo: Literal["multiesporte", "modalidade_sem_metricas", "sem_tipo", "divergente"] | None = None
    texto: str | None = None  # so em `sem_linha_base`: "Sem linha de base: ..."
    modalidade: str
    tipo_treino: str | None
    janela_semanas: int
    minimo_treinos: int
    metricas: list[MetricaBaseOut]  # [] em `sem_linha_base`


class CargaPseOut(BaseModel):
    """Carga pela PSE da atividade (`carga_pse@1`, ADR 0012, item 6): PSE x minutos, em UA. Calculada na leitura; separada da `carga@2`
    (escalas diferentes, nao se somam). Nao traz a observacao nem a sensacao."""

    versao: str
    estado: Literal["calculada", "sem_checkin", "sem_duracao"]
    pse: int | None = None  # null em `sem_checkin`
    minutos: float  # duracao_s / 60, tempo de cronometro
    valor: float | None = None  # UA, sem arredondar; so em `calculada`
    valor_texto: str | None = None  # "270 UA", "272,5 UA" (1 casa quando nao e inteiro)
    texto: str  # "Carga pela PSE: 6 x 45 min = 270 UA." (ou "6 x 45 min 25 s = 272,5 UA.") ou o motivo de nao haver valor


class FeedbackOut(BaseModel):
    """Feedback automatico do treino (ADR 0013, item 2): cinco estados e a `mensagem` pronta, que o app mostra como veio.

    Dado de saude (derivado do check-in): so no `GET` da atividade do proprio atleta, nunca em lista. Nunca traz o texto de um
    feedback desatualizado, o texto reprovado, o provedor, o modelo nem a versao dos fatos.
    """

    estado: Literal["pronto", "sem_checkin", "pendente", "desatualizado", "indisponivel"]
    texto: str | None = None  # so em `pronto` (3 a 5 linhas)
    origem: Literal["automatico", "teste"] | None = None  # so em `pronto`; `teste` = provedor falso, nunca texto de verdade
    mensagem: str | None = None  # frase pronta em portugues, em todos os estados menos `pronto`
    checkin_aberto: bool | None = None  # so em `sem_checkin`; falso = prazo vencido (sem botao)
    motivo: Literal["texto_reprovado", "provedor_erro", "provedor_tempo_limite", "provedor_nao_configurado",
                    "limite_de_chamadas"] | None = None  # so em `indisponivel`; codigo para quem cuida do app, o app nao o mostra


class AtividadeOut(BaseModel):
    """A atividade como a API mostra. A posicao de inicio nunca sai (ADR 0007)."""

    atividade_id: int
    modalidade: str
    subtipo: str | None
    inicio: datetime  # UTC
    duracao_s: float
    distancia_m: float | None
    fc_media: float | None
    clima: ClimaOut | None = None  # campo novo e opcional
    esforcos: EsforcosOut | None = None  # so corrida e ciclismo (ADR 0008); null nas outras modalidades
    transicao: TransicaoOut = Field(default_factory=lambda: TransicaoOut(valor=False))  # ADR 0009; sem linha = false/null
    carga: CargaAtividadeOut | None = None  # null so em multiesporte_pai e troca; elegivel nao calculada vem `pendente`
    tipo_treino: Literal["leve", "moderado", "longo", "intervalado", "fartlek"] | None = None  # ADR 0011 (#266)
    tipo_origem: Literal["sugestao", "professor", "trainingpeaks", "semana_padrao"] | None = None
    tipo_confirmado: bool = False
    tipo_divergencia: DivergenciaOut | None = None
    linha_base: LinhaBaseOut | None = None
    # Check-in pos-treino (ADR 0012, #298): dado de saude, so do proprio atleta; nunca nas listas.
    checkin: CheckinOut | None = None  # null: sem check-in ou atividade que nao pede (multiesporte_pai e troca)
    checkin_aberto: bool = False  # false em pai/troca e quando o prazo de criacao passou sem check-in; true se ja existe (editar nao tem prazo)
    pse_sugerida: int | None = None  # numa parte de multiesporte: a PSE do check-in da parte anterior, se houver
    carga_pse: CargaPseOut | None = None  # null so em multiesporte_pai e troca; sem check-in vem `sem_checkin`
    feedback: FeedbackOut | None = None  # ADR 0013, #328; null em multiesporte_pai e troca (o cartao nao aparece)
    # Campos prontos para a tela (#158): a API formata, o app mostra (ADR 0004, adendo 2).
    data_local: str  # AAAA-MM-DD, pelo fuso da atividade (ADR 0003)
    hora_local: str  # HH:MM, pelo fuso da atividade
    duracao: str  # h:mm:ss (horas sem limite, segundos arredondados com meio para cima)
    pace_medio: str | None = None  # m:ss por km; so corrida com distancia (formatar_pace)
    distancia: str | None = None  # "10,00 km"; natacao em metros ("1.800 m"); null sem distancia (#216)


ATRIBUICAO_CLIMA = "Weather data by Open-Meteo.com"
MODALIDADES_COM_PACE = ("corrida",)


def _duracao_hms(duracao_s: float) -> str:
    return checkin_svc.duracao_hms(duracao_s)


def _pace_medio(a: Atividade) -> str | None:
    if a.modalidade not in MODALIDADES_COM_PACE or not a.distancia_m or a.distancia_m <= 0 or a.duracao_s <= 0:
        return None
    return formatar_pace(a.duracao_s / (a.distancia_m / 1000))


def _num(x: float | None) -> float | None:
    return None if x is None else round(x, 1)


def _distancia_texto(m: float | None) -> str | None:
    if m is None:
        return None
    if m < 1000:
        return f"{int(m + 0.5)} m"
    return f"{m / 1000:.2f}".replace(".", ",") + " km"


def _faixa_rotulo(faixa: str | None) -> str | None:
    if not faixa:
        return None
    return f"{faixa[1:]} m" if faixa[0] == "d" else f"{faixa[1:]} min"


def _bloco_out(b, modalidade: str) -> BlocoOut:
    corrida = modalidade == ef.MODALIDADE_CORRIDA
    vel = b.distancia_m / b.duracao_s * 3.6 if b.distancia_m and b.duracao_s > 0 else None
    return BlocoOut(
        ordem=b.ordem,
        categoria=b.categoria,
        faixa=b.faixa,
        faixa_rotulo=_faixa_rotulo(b.faixa),
        treino_chave=bool(b.treino_chave),
        inicio_offset_s=_num(b.inicio_offset_s),
        duracao_s=_num(b.duracao_s),
        distancia_m=_num(b.distancia_m),
        parada_apos_s=_num(b.parada_apos_s),
        fc_media=_num(b.fc_media),
        pace_s_km=_num(b.pace_s_km) if corrida else None,
        velocidade_kmh=_num(vel) if not corrida else None,
        duracao=formatar_pace(b.duracao_s),  # a regra unica de m:ss do projeto
        distancia=_distancia_texto(b.distancia_m),
        pace=formatar_pace(b.pace_s_km) if corrida and b.pace_s_km else None,
        velocidade=f"{vel:.1f}".replace(".", ",") + " km/h" if not corrida and vel else None,
        parada_apos=formatar_pace(b.parada_apos_s) if b.parada_apos_s else None,
    )


def _esforcos_out(session: Session, a: Atividade) -> EsforcosOut | None:
    e = esforcos_da_atividade(session, a)
    if e is None:
        return None
    return EsforcosOut(
        versao=e.versao,
        referencia_da_atividade=e.ref_origem == ef.REF_ATIVIDADE,
        treino_chave=e.treino_chave,
        blocos=[_bloco_out(b, a.modalidade) for b in e.blocos],
    )


def _clima_out(c: ClimaDaAtividade) -> ClimaOut:
    return ClimaOut(
        estado=c.estado,
        temperatura_c=c.temperatura_c,
        sensacao_c=c.sensacao_c,
        umidade_pct=c.umidade_pct,
        vento_kmh=c.vento_kmh,
        atribuicao=ATRIBUICAO_CLIMA if c.estado == "ok" else None,
    )


def _carga_pse_out(c: CargaPseLida | None) -> CargaPseOut | None:
    return None if c is None else CargaPseOut.model_validate(asdict(c))


def _feedback(session: Session, a: Atividade) -> FeedbackLido | None:
    """O cartao do feedback; a noite do treino so e lida quando ja ha feedback gravado (ADR 0014, item 4b)."""
    aberto = checkin_svc.checkin_aberto(a, a.checkin is not None)
    if a.checkin is None or a.checkin.feedback is None:
        return feedback_da_atividade(a, a.checkin, aberto)
    hoje = importado_em_de_hoje(carregar_da_atividade(session, a), a)
    return feedback_da_atividade(a, a.checkin, aberto, recuperacao_hoje=hoje)


def _feedback_out(f: FeedbackLido | None) -> FeedbackOut | None:
    return None if f is None else FeedbackOut(**asdict(f))


def _carga_out(c: CargaLida) -> CargaAtividadeOut:
    return CargaAtividadeOut(estado=c.estado, carga=c.carga, metodo=c.metodo, cobertura_pct=c.cobertura_pct,
                             motivo=c.motivo, versao=c.versao)


def get_fit_dir() -> Path | None:
    """Pasta dos FIT guardados; `None` = `FIT_DIR` da configuração. Os testes trocam por um diretório temporário."""
    return None


def _ler_limitado(arquivo: UploadFile) -> bytes:
    """Lê em pedaços e para em 10 MB + 1: o limite vale pelos bytes realmente lidos, não pelo Content-Length."""
    partes: list[bytes] = []
    total = 0
    while True:
        parte = arquivo.file.read(PEDACO)
        if not parte:
            return b"".join(partes)
        total += len(parte)
        if total > TAMANHO_MAX_FIT:
            raise HTTPException(status_code=413, detail="arquivo acima de 10 MB")
        partes.append(parte)


@router.post(
    "/fit",
    status_code=201,
    response_model=UploadFitOut,
    operation_id="enviarAtividadeFit",
    responses={
        200: {"model": UploadFitOut, "description": "Atividade que já existia (atualizada ou ignorada)"},
        201: {"model": UploadFitOut, "description": "Atividade inserida"},
        400: {"model": Erro, "description": "FIT inválido ou que não é uma atividade, ou extensão diferente de .fit"},
        404: {"model": Erro, "description": "Atleta não encontrado"},
        413: {"model": Erro, "description": "Arquivo acima de 10 MB"},
    },
)
def enviar_atividade_fit(
    atleta_id: int,
    response: Response,
    arquivo: UploadFile = File(..., description="Arquivo .fit de uma atividade (até 10 MB)"),
    session: Session = Depends(get_session),
    fit_dir: Path | None = Depends(get_fit_dir),
) -> UploadFitOut:
    """Envia um FIT (campo multipart `arquivo`). `201` se a atividade é nova; `200` se já existia."""
    if session.get(Atleta, atleta_id) is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")
    if not (arquivo.filename or "").lower().endswith(".fit"):
        raise HTTPException(status_code=400, detail="o arquivo precisa ter extensão .fit")
    conteudo = _ler_limitado(arquivo)
    try:
        r = importar_fit(session, atleta_id, conteudo, fit_dir)
    except AtletaInexistente:
        raise HTTPException(status_code=404, detail="atleta não encontrado") from None
    except FitGrande:
        raise HTTPException(status_code=413, detail="arquivo acima de 10 MB") from None
    except FitNaoEAtividade:
        raise HTTPException(status_code=400, detail="o arquivo é um FIT, mas não é uma atividade") from None
    except FitInvalido:
        raise HTTPException(status_code=400, detail="FIT inválido ou corrompido") from None
    if r.resultado != "inserida":
        response.status_code = 200
    return UploadFitOut(resultado=r.resultado, atividade_id=r.atividade_id, avisos=r.avisos)


@router.get(
    "/{atividade_id}",
    response_model=AtividadeOut,
    operation_id="buscarAtividade",
    responses={404: {"model": Erro, "description": "Atleta ou atividade não encontrados (atividade de outro atleta também)"}},
)
def buscar_atividade(
    atleta_id: int,
    atividade_id: int,
    session: Session = Depends(get_session),
) -> AtividadeOut:
    """A atividade com o `clima` (ADR 0007). `indoor`, `sem_posicao`, `pendente` e `falha` dizem por que não há valores."""
    if session.get(Atleta, atleta_id) is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")
    a = session.get(Atividade, atividade_id, options=[joinedload(Atividade.checkin).joinedload(CheckinTreino.feedback)])  # LEFT JOIN: sem consulta extra
    if a is None or a.atleta_id != atleta_id:
        raise HTTPException(status_code=404, detail="atividade não encontrada")
    clima = clima_da_atividade(session, atividade_id)
    local = inicio_local(a.inicio, a.fuso_min)
    carga = carga_da_atividade(session, a)
    div = texto_divergencia(a)
    return AtividadeOut(
        atividade_id=a.id,
        modalidade=a.modalidade,
        subtipo=a.subtipo,
        inicio=a.inicio,
        duracao_s=a.duracao_s,
        distancia_m=a.distancia_m,
        fc_media=a.fc_media,
        clima=None if clima is None else _clima_out(clima),
        esforcos=_esforcos_out(session, a),
        transicao=transicao_da_atividade(session, a.id),
        carga=None if carga is None else _carga_out(carga),
        tipo_treino=a.tipo_treino,
        tipo_origem=a.tipo_origem,
        tipo_confirmado=bool(a.tipo_confirmado),
        tipo_divergencia=None if div is None else DivergenciaOut(motivo=div[0], texto=div[1]),
        linha_base=LinhaBaseOut.model_validate(asdict(linha_base_da_atividade(session, a))),
        checkin=None if a.checkin is None else checkin_out(a.checkin),
        checkin_aberto=checkin_svc.checkin_aberto(a, a.checkin is not None),
        feedback=_feedback_out(_feedback(session, a)),
        pse_sugerida=checkin_svc.pse_sugerida(session, a),
        carga_pse=_carga_pse_out(carga_pse_da_atividade(a, a.checkin)),
        data_local=local.date().isoformat(),
        hora_local=local.strftime("%H:%M"),
        duracao=_duracao_hms(a.duracao_s),
        pace_medio=_pace_medio(a),
        distancia=distancia_da_atividade(a.modalidade, a.distancia_m),
    )
