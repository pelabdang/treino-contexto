import { StyleSheet, Text, View } from "react-native";

export default function Inicio() {
  return (
    <View style={styles.container}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Evolução dos tiros de 1 km
      </Text>
      <Text style={styles.texto}>Em construção: aqui vai o gráfico da sua evolução.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: "center", backgroundColor: "#fff" },
  titulo: { fontSize: 24, fontWeight: "700", marginBottom: 12, color: "#111" },
  texto: { fontSize: 16, color: "#444" },
});
