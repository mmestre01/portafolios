import Phaser from "phaser";
import "./style.css";
import { gameConfig } from "./config/gameConfig";
import { GameScene, type FinalStats } from "./game/GameScene";

const startOverlay = document.querySelector<HTMLDivElement>("#start-overlay");
const endOverlay = document.querySelector<HTMLDivElement>("#end-overlay");
const playButton = document.querySelector<HTMLButtonElement>("#play-button");
const restartButton = document.querySelector<HTMLButtonElement>("#restart-button");
const soundToggle = document.querySelector<HTMLButtonElement>("#sound-toggle");
const finalStats = document.querySelector<HTMLElement>("#final-stats");
const giftMessage = document.querySelector<HTMLElement>("#gift-message");

let soundEnabled = true;

const renderFinalStats = (stats: FinalStats) => {
  if (!finalStats || !giftMessage) return;
  finalStats.innerHTML = `
    <dt>Puntuación</dt><dd>${stats.score}</dd>
    <dt>Problemas destruidos</dt><dd>${stats.badDestroyed}</dd>
    <dt>Cafés y dulces protegidos</dt><dd>${stats.treatsProtected}</dd>
    <dt>Cosas buenas destruidas</dt><dd>${stats.goodDestroyed}</dd>
  `;
  giftMessage.textContent = gameConfig.messages.gift;
};

const scene = new GameScene({
  onVictory: (stats) => {
    renderFinalStats(stats);
    endOverlay?.classList.remove("hidden");
  },
  onSoundRequest: () => soundEnabled
});

const game = new Phaser.Game({
  type: Phaser.CANVAS,
  parent: "game-container",
  width: gameConfig.gameplay.width,
  height: gameConfig.gameplay.height,
  backgroundColor: "#151722",
  scene,
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH
  },
  physics: {
    default: "arcade",
    arcade: {
      debug: false
    }
  },
  render: {
    antialias: true,
    pixelArt: false
  }
});

if (import.meta.env.DEV) {
  (window as Window & { __felices26GemaGame?: Phaser.Game }).__felices26GemaGame = game;
}

playButton?.addEventListener("click", () => {
  startOverlay?.classList.add("hidden");
  game.scene.getScene("GameScene").events.emit("start-run", soundEnabled);
});

restartButton?.addEventListener("click", () => {
  endOverlay?.classList.add("hidden");
  game.scene.getScene("GameScene").events.emit("restart-run", soundEnabled);
});

soundToggle?.addEventListener("click", () => {
  soundEnabled = !soundEnabled;
  soundToggle.textContent = `Sonido: ${soundEnabled ? "sí" : "no"}`;
  game.scene.getScene("GameScene").events.emit("sound-toggle", soundEnabled);
});
