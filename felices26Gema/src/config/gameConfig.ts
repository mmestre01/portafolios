export const gameConfig = {
  friend: {
    name: "Gema",
    age: 26,
    faceAsset: "assets/gema-face.png?v=20260717-1214"
  },
  route: {
    basePath: "/felices26Gema/"
  },
  gameplay: {
    width: 390,
    height: 780,
    normalDurationSeconds: 45,
    maxPatience: 100,
    initialPatience: 100,
    baseFireIntervalMs: 450,
    rapidFireIntervalMs: 220,
    rapidFireDurationMs: 8000,
    doubleShotDurationMs: 8000,
    goodItemPenalty: 15,
    badItemMissPenalty: 10,
    directHitPenalty: 12,
    bossHitPenalty: 12
  },
  boss: {
    name: "UCAM",
    asset: "assets/ucam-logo.png?v=20260717-1214",
    health: 110,
    estimatedDurationSeconds: 35
  },
  messages: {
    title: "FELICES 26, GEMA",
    intro: [
      "Destruye los problemas.",
      "Protege el café y los dulces.",
      "Sobrevive a la UCAM."
    ],
    patienceEmpty: [
      "Paciencia agotada.",
      "Reiniciando tolerancia humana..."
    ],
    victory: [
      "¡FELICES 26, GEMA!",
      "UCAM derrotada.",
      "Paciencia parcialmente conservada."
    ],
    gift: "Muchas felicidades, Gema. Ojalá estar siempre a tu lado."
  }
} as const;

export type GameConfig = typeof gameConfig;
