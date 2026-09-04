import Phaser from "phaser";
import { gameConfig } from "../config/gameConfig";

type ItemKind = "exam" | "mail" | "pdf" | "weights" | "coffee" | "sweet" | "cake";
type RunState = "idle" | "playing" | "resetting" | "boss" | "victory";

type FallingItem = Phaser.GameObjects.Container & {
  body: Phaser.Physics.Arcade.Body;
  kind: ItemKind;
  good: boolean;
  hp: number;
  maxHp: number;
  speed: number;
  wave: number;
  baseX: number;
  activeItem: boolean;
};

type Shot = Phaser.GameObjects.Container & {
  body: Phaser.Physics.Arcade.Body;
};

type BossShot = Phaser.GameObjects.Ellipse & {
  body: Phaser.Physics.Arcade.Body;
};

type BossContainer = Phaser.GameObjects.Container & {
  body: Phaser.Physics.Arcade.Body;
  hp: number;
  maxHp: number;
  logo: Phaser.GameObjects.Image;
  direction: number;
};

export type FinalStats = {
  score: number;
  badDestroyed: number;
  treatsProtected: number;
  goodDestroyed: number;
};

type GameSceneHooks = {
  onVictory: (stats: FinalStats) => void;
  onSoundRequest: () => boolean;
};

const W = gameConfig.gameplay.width;
const H = gameConfig.gameplay.height;
const playerY = H - 92;

export class GameScene extends Phaser.Scene {
  private hooks: GameSceneHooks;
  private state: RunState = "idle";
  private player!: Phaser.GameObjects.Container;
  private playerBody!: Phaser.Physics.Arcade.Body;
  private face!: Phaser.GameObjects.Image;
  private faceMask!: Phaser.GameObjects.Graphics;
  private flame!: Phaser.GameObjects.Triangle;
  private bullets!: Phaser.Physics.Arcade.Group;
  private items!: Phaser.Physics.Arcade.Group;
  private bossBullets!: Phaser.Physics.Arcade.Group;
  private targetX: number = W / 2;
  private cursors?: Phaser.Types.Input.Keyboard.CursorKeys;
  private keyA?: Phaser.Input.Keyboard.Key;
  private keyD?: Phaser.Input.Keyboard.Key;
  private spawnTimer?: Phaser.Time.TimerEvent;
  private fireTimer?: Phaser.Time.TimerEvent;
  private bossFireTimer?: Phaser.Time.TimerEvent;
  private bossExtraTimer?: Phaser.Time.TimerEvent;
  private normalStart: number = 0;
  private patience: number = gameConfig.gameplay.initialPatience;
  private displayPatience: number = gameConfig.gameplay.initialPatience;
  private score: number = 0;
  private badDestroyed: number = 0;
  private treatsProtected: number = 0;
  private goodDestroyed: number = 0;
  private rapidUntil: number = 0;
  private doubleUntil: number = 0;
  private invulnerableUntil: number = 0;
  private bossWarningShown = false;
  private pointerHeld = false;
  private soundEnabled = true;
  private floatingMessages: Phaser.GameObjects.Text[] = [];
  private hud!: {
    score: Phaser.GameObjects.Text;
    patienceFill: Phaser.GameObjects.Rectangle;
    patienceBg: Phaser.GameObjects.Rectangle;
    patienceText: Phaser.GameObjects.Text;
    bonus: Phaser.GameObjects.Text;
    bossBarBg: Phaser.GameObjects.Rectangle;
    bossBarFill: Phaser.GameObjects.Rectangle;
    bossText: Phaser.GameObjects.Text;
  };
  private boss?: BossContainer;

  constructor(hooks: GameSceneHooks) {
    super("GameScene");
    this.hooks = hooks;
  }

  preload() {
    this.load.image("gema-face", gameConfig.friend.faceAsset);
    this.load.image("ucam-logo", gameConfig.boss.asset);
  }

  create() {
    this.createBackground();
    this.createPlayer();
    this.createGroups();
    this.createHud();
    this.setupInput();
    this.setupEvents();
  }

  update(time: number, delta: number) {
    if (this.state === "idle" || this.state === "victory") return;
    this.updatePlayer(delta);
    this.updateBullets();
    this.updateItems(time, delta);
    this.updateBoss(delta);
    this.updateBossHits();
    this.updateHud(time);
    if (this.state === "playing" && time - this.normalStart > gameConfig.gameplay.normalDurationSeconds * 1000) {
      this.startBoss();
    }
  }

  private setupEvents() {
    this.events.on("start-run", (soundEnabled: boolean) => this.startRun(soundEnabled));
    this.events.on("restart-run", (soundEnabled: boolean) => this.startRun(soundEnabled));
    this.events.on("sound-toggle", (soundEnabled: boolean) => {
      this.soundEnabled = soundEnabled;
    });
  }

  private createBackground() {
    const g = this.add.graphics();
    g.fillGradientStyle(0x191b28, 0x191b28, 0x11131c, 0x171523, 1);
    g.fillRect(0, 0, W, H);
    for (let i = 0; i < 80; i += 1) {
      const x = Phaser.Math.Between(18, W - 18);
      const y = Phaser.Math.Between(24, H - 18);
      const alpha = Phaser.Math.FloatBetween(0.12, 0.45);
      g.fillStyle(0xffffff, alpha);
      g.fillCircle(x, y, Phaser.Math.FloatBetween(0.6, 1.7));
    }
    g.lineStyle(1, 0x33435f, 0.35);
    for (let x = 28; x < W; x += 42) g.lineBetween(x, 82, x - 35, H);
  }

  private createPlayer() {
    this.player = this.add.container(W / 2, playerY);
    const ship = this.add.graphics();
    ship.fillStyle(0x45d6ff, 1);
    ship.fillTriangle(-44, 30, 0, -30, 44, 30);
    ship.fillStyle(0xffe066, 1);
    ship.fillTriangle(-22, 18, 0, -12, 22, 18);
    ship.lineStyle(4, 0xf8f7f2, 0.9);
    ship.strokeCircle(0, -8, 31);
    this.face = this.add.image(0, -8, "gema-face").setDisplaySize(54, 54);
    this.faceMask = this.make.graphics({ x: 0, y: 0 }, false);
    this.face.setMask(this.faceMask.createGeometryMask());
    this.flame = this.add.triangle(0, 40, 0, 0, -9, 28, 9, 28, 0xff7c3a, 0.9);
    this.player.add([this.flame, ship, this.face]);
    this.physics.add.existing(this.player);
    this.playerBody = this.player.body as Phaser.Physics.Arcade.Body;
    this.playerBody.setSize(48, 46);
    this.playerBody.setOffset(-24, -16);
    this.updateFaceMask();
  }

  private createGroups() {
    this.bullets = this.physics.add.group({ maxSize: 42, runChildUpdate: false });
    this.items = this.physics.add.group({ maxSize: 34, runChildUpdate: false });
    this.bossBullets = this.physics.add.group({ maxSize: 18, runChildUpdate: false });
    this.physics.add.overlap(this.bullets, this.items, (shot, item) => this.hitItem(shot as Shot, item as FallingItem));
    this.physics.add.overlap(this.items, this.player, (_player, item) => this.playerHitByItem(item as FallingItem));
    this.physics.add.overlap(this.bossBullets, this.player, (_player, shot) => this.playerHitByBossShot(shot as BossShot));
  }

  private createHud() {
    const safeTop = 16;
    this.add.text(18, safeTop, "PACIENCIA", {
      color: "#f8f7f2",
      fontFamily: "sans-serif",
      fontSize: "13px",
      fontStyle: "700"
    }).setDepth(20);
    this.hud = {
      score: this.add.text(W - 18, safeTop, "0", {
        color: "#fff6c7",
        fontFamily: "sans-serif",
        fontSize: "16px",
        fontStyle: "800"
      }).setOrigin(1, 0).setDepth(20),
      patienceBg: this.add.rectangle(18, safeTop + 25, W - 36, 12, 0x33394e, 1).setOrigin(0, 0).setDepth(20),
      patienceFill: this.add.rectangle(18, safeTop + 25, W - 36, 12, 0x64df8a, 1).setOrigin(0, 0).setDepth(21),
      patienceText: this.add.text(W - 18, safeTop + 16, "100%", {
        color: "#f8f7f2",
        fontFamily: "sans-serif",
        fontSize: "12px",
        fontStyle: "700"
      }).setOrigin(1, 0).setDepth(22),
      bonus: this.add.text(W / 2, safeTop + 44, "", {
        color: "#90f1ff",
        fontFamily: "sans-serif",
        fontSize: "13px",
        fontStyle: "800",
        stroke: "#10121a",
        strokeThickness: 4
      }).setOrigin(0.5, 0).setDepth(22),
      bossBarBg: this.add.rectangle(60, safeTop + 60, W - 120, 10, 0x33394e, 1).setOrigin(0, 0).setDepth(20).setVisible(false),
      bossBarFill: this.add.rectangle(60, safeTop + 60, W - 120, 10, 0xff596d, 1).setOrigin(0, 0).setDepth(21).setVisible(false),
      bossText: this.add.text(W / 2, safeTop + 72, "", {
        color: "#ffccd2",
        fontFamily: "sans-serif",
        fontSize: "12px",
        fontStyle: "800"
      }).setOrigin(0.5, 0).setDepth(22).setVisible(false)
    };
  }

  private setupInput() {
    this.input.on("pointermove", (pointer: Phaser.Input.Pointer) => {
      if (pointer.isDown) {
        this.pointerHeld = true;
        this.targetX = Phaser.Math.Clamp(pointer.x, 42, W - 42);
      }
    });
    this.input.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
      this.pointerHeld = true;
      this.targetX = Phaser.Math.Clamp(pointer.x, 42, W - 42);
    });
    this.input.on("pointerup", () => {
      this.pointerHeld = false;
    });
    this.input.on("pointerupoutside", () => {
      this.pointerHeld = false;
    });
    this.cursors = this.input.keyboard?.createCursorKeys();
    this.keyA = this.input.keyboard?.addKey(Phaser.Input.Keyboard.KeyCodes.A);
    this.keyD = this.input.keyboard?.addKey(Phaser.Input.Keyboard.KeyCodes.D);
  }

  private startRun(soundEnabled: boolean) {
    this.soundEnabled = soundEnabled;
    this.clearTimers();
    this.clearObjects();
    this.state = "playing";
    this.normalStart = this.time.now;
    this.patience = gameConfig.gameplay.initialPatience;
    this.displayPatience = this.patience;
    this.score = 0;
    this.badDestroyed = 0;
    this.treatsProtected = 0;
    this.goodDestroyed = 0;
    this.rapidUntil = 0;
    this.doubleUntil = 0;
    this.invulnerableUntil = this.time.now + 1400;
    this.bossWarningShown = false;
    this.pointerHeld = false;
    this.player.setPosition(W / 2, playerY).setAlpha(1).setActive(true).setVisible(true);
    this.targetX = W / 2;
    this.hud.bossBarBg.setVisible(false);
    this.hud.bossBarFill.setVisible(false);
    this.hud.bossText.setVisible(false);
    this.showCenterNotice(["FELICES 26, GEMA"], 900);
    this.spawnTimer = this.time.addEvent({
      delay: 930,
      loop: true,
      callback: () => this.spawnFallingItem()
    });
    this.resetFireTimer();
  }

  private clearTimers() {
    this.spawnTimer?.remove(false);
    this.fireTimer?.remove(false);
    this.bossFireTimer?.remove(false);
    this.bossExtraTimer?.remove(false);
  }

  private clearObjects() {
    this.bullets?.clear(true, true);
    this.items?.clear(true, true);
    this.bossBullets?.clear(true, true);
    this.boss?.destroy();
    this.boss = undefined;
    this.floatingMessages.forEach((message) => message.destroy());
    this.floatingMessages = [];
  }

  private updatePlayer(delta: number) {
    const speed = 0.018 * delta;
    if (this.cursors?.left.isDown || this.keyA?.isDown) this.targetX -= 0.42 * delta;
    if (this.cursors?.right.isDown || this.keyD?.isDown) this.targetX += 0.42 * delta;
    this.targetX = Phaser.Math.Clamp(this.targetX, 42, W - 42);
    this.player.x = Phaser.Math.Linear(this.player.x, this.targetX, Phaser.Math.Clamp(speed, 0, 0.28));
    this.player.y = playerY;
    this.updateFaceMask();
    this.flame.scaleY = 0.75 + Math.sin(this.time.now * 0.018) * 0.18;
    if (this.time.now < this.invulnerableUntil) {
      this.player.alpha = 0.55 + Math.sin(this.time.now * 0.028) * 0.28;
    } else {
      this.player.alpha = 1;
    }
  }

  private updateFaceMask() {
    this.faceMask.clear();
    this.faceMask.fillStyle(0xffffff);
    this.faceMask.fillCircle(this.player.x, this.player.y - 8, 27);
  }

  private updateBullets() {
    this.bullets.children.each((child) => {
      const shot = child as Shot;
      if (shot.active && shot.y < -20) this.bullets.killAndHide(shot);
      return true;
    });
    this.bossBullets.children.each((child) => {
      const shot = child as BossShot;
      if (shot.active && shot.y > H + 30) this.bossBullets.killAndHide(shot);
      return true;
    });
  }

  private updateItems(time: number, delta: number) {
    this.items.children.each((child) => {
      const item = child as FallingItem;
      if (!item.activeItem) return true;
      item.y += item.speed * delta;
      if (item.wave > 0) item.x = Phaser.Math.Clamp(item.baseX + Math.sin(time * 0.0035 + item.y * 0.015) * item.wave, 32, W - 32);
      item.angle += item.good ? Math.sin(time * 0.003) * 0.08 : 0.04;
      if (item.y > H + 48) this.itemReachedBottom(item);
      return true;
    });
  }

  private updateBoss(delta: number) {
    if (!this.boss || this.state !== "boss") return;
    this.boss.x += this.boss.direction * 0.085 * delta;
    if (this.boss.x < 84 || this.boss.x > W - 84) this.boss.direction *= -1;
    if (this.boss.y < 134) this.boss.y += 0.04 * delta;
  }

  private updateBossHits() {
    if (!this.boss || this.state !== "boss") return;
    const bossLeft = this.boss.x - 76;
    const bossRight = this.boss.x + 76;
    const bossTop = this.boss.y - 48;
    const bossBottom = this.boss.y + 48;
    this.bullets.children.each((child) => {
      const shot = child as Shot;
      if (
        shot.active &&
        shot.x >= bossLeft &&
        shot.x <= bossRight &&
        shot.y >= bossTop &&
        shot.y <= bossBottom
      ) {
        this.hitBoss(shot);
      }
      return true;
    });
  }

  private updateHud(time: number) {
    this.displayPatience = Phaser.Math.Linear(this.displayPatience, this.patience, 0.12);
    const ratio = Phaser.Math.Clamp(this.displayPatience / gameConfig.gameplay.maxPatience, 0, 1);
    this.hud.patienceFill.width = (W - 36) * ratio;
    this.hud.patienceFill.fillColor = ratio < 0.3 ? 0xff596d : ratio < 0.58 ? 0xffc857 : 0x64df8a;
    this.hud.patienceText.setText(`${Math.round(this.displayPatience)}%`);
    this.hud.score.setText(`${this.score}`);
    const rapid = Math.max(0, Math.ceil((this.rapidUntil - time) / 1000));
    const dbl = Math.max(0, Math.ceil((this.doubleUntil - time) / 1000));
    const secondsToBoss = Math.max(
      0,
      Math.ceil((gameConfig.gameplay.normalDurationSeconds * 1000 - (time - this.normalStart)) / 1000)
    );
    if (this.state === "playing" && secondsToBoss <= 10 && !this.bossWarningShown) {
      this.bossWarningShown = true;
      this.showCenterNotice(["UCAM se acerca"], 900);
    }
    const bossCountdown =
      this.state === "playing" ? `UCAM EN ${secondsToBoss}s` : "";
    const bonuses = [
      rapid > 0 ? `CAFEINA ${rapid}s` : "",
      dbl > 0 ? `AZUCAR ${dbl}s` : "",
      bossCountdown
    ].filter(Boolean);
    this.hud.bonus.setText(bonuses.join("  "));
    if (this.boss) {
      this.hud.bossBarFill.width = (W - 120) * Phaser.Math.Clamp(this.boss.hp / this.boss.maxHp, 0, 1);
    }
  }

  private resetFireTimer() {
    this.fireTimer?.remove(false);
    const delay = this.time.now < this.rapidUntil ? gameConfig.gameplay.rapidFireIntervalMs : gameConfig.gameplay.baseFireIntervalMs;
    this.fireTimer = this.time.addEvent({
      delay,
      loop: true,
      callback: () => {
        this.fire();
        const desired = this.time.now < this.rapidUntil ? gameConfig.gameplay.rapidFireIntervalMs : gameConfig.gameplay.baseFireIntervalMs;
        if (this.fireTimer && this.fireTimer.delay !== desired) this.resetFireTimer();
      }
    });
  }

  private fire() {
    if (this.state !== "playing" && this.state !== "boss") return;
    if (!this.isFiringInputActive()) return;
    const offsets = this.time.now < this.doubleUntil ? [-13, 13] : [0];
    offsets.forEach((offset) => {
      const shot = this.acquireShot();
      shot.setActive(true).setVisible(true).setPosition(this.player.x + offset, this.player.y - 45);
      shot.body.enable = true;
      shot.body.setSize(16, 58);
      shot.body.setOffset(-8, -34);
      shot.body.setVelocityY(-610);
    });
    this.playTone(880, 0.025, "square", 0.035);
  }

  private acquireShot(): Shot {
    return (this.bullets.getFirstDead(false) as Shot | null) ?? this.createShot();
  }

  private isFiringInputActive() {
    return Boolean(
      this.pointerHeld ||
        this.cursors?.left.isDown ||
        this.cursors?.right.isDown ||
        this.keyA?.isDown ||
        this.keyD?.isDown
    );
  }

  private createShot(): Shot {
    const shot = this.add.container(0, 0) as Shot;
    const outer = this.add.rectangle(0, 0, 20, 64, 0x7cf7ff, 0.22);
    const beam = this.add.graphics();
    beam.fillStyle(0x7cf7ff, 0.95);
    beam.fillRoundedRect(-4, -29, 8, 58, 4);
    beam.fillStyle(0xffffff, 1);
    beam.fillRoundedRect(-1.5, -26, 3, 52, 2);
    beam.fillStyle(0xb15cff, 1);
    beam.fillTriangle(0, -42, -10, -24, 10, -24);
    beam.fillTriangle(0, 42, -7, 27, 7, 27);
    const spark = this.add.circle(0, -36, 6, 0xffffff, 0.85);
    shot.add([outer, beam, spark]);
    shot.setDepth(12);
    this.physics.add.existing(shot);
    this.bullets.add(shot);
    return shot;
  }

  private spawnFallingItem(forcedKind?: ItemKind) {
    if (this.state !== "playing" && this.state !== "boss") return;
    const progress = Phaser.Math.Clamp((this.time.now - this.normalStart) / (gameConfig.gameplay.normalDurationSeconds * 1000), 0, 1);
    const kind = forcedKind ?? this.pickKind(progress);
    const item = this.createItem(kind);
    const x = Phaser.Math.Between(42, W - 42);
    item.setPosition(x, -42);
    item.baseX = x;
    item.speed = this.itemSpeed(kind, progress);
    item.wave = kind === "mail" ? 22 : 0;
    item.activeItem = true;
    item.setActive(true).setVisible(true);
    item.body.enable = true;
    item.body.setSize(kind === "pdf" ? 66 : 48, kind === "pdf" ? 58 : 44);
    item.body.setOffset(kind === "pdf" ? -33 : -24, kind === "pdf" ? -29 : -22);
  }

  private pickKind(progress: number): ItemKind {
    const roll = Math.random();
    const goodChance = 0.27;
    if (roll < goodChance) return Phaser.Math.RND.pick(["coffee", "sweet", "cake"]);
    if (roll > 0.77 - progress * 0.14) return "pdf";
    return Phaser.Math.RND.pick(["exam", "mail", "weights"]);
  }

  private itemSpeed(kind: ItemKind, progress: number) {
    const base = kind === "mail" ? 0.19 : kind === "pdf" ? 0.105 : kind === "weights" ? 0.115 : kind === "cake" ? 0.12 : 0.15;
    return base + progress * 0.045;
  }

  private createItem(kind: ItemKind): FallingItem {
    const item = this.add.container(0, 0) as FallingItem;
    const spec = this.itemSpec(kind);
    if (spec.good) {
      item.add(this.add.circle(0, 0, Math.max(spec.w, spec.h) / 2 + 8, 0x7dffb0, 0.15));
    }
    item.add(this.createItemIcon(kind));
    this.physics.add.existing(item);
    this.items.add(item);
    item.kind = kind;
    item.good = spec.good;
    item.hp = spec.hp;
    item.maxHp = spec.hp;
    return item;
  }

  private itemSpec(kind: ItemKind) {
    const specs = {
      exam: { good: false, hp: 1, w: 58, h: 48 },
      mail: { good: false, hp: 1, w: 58, h: 44 },
      pdf: { good: false, hp: 3, w: 74, h: 64 },
      weights: { good: false, hp: 2, w: 70, h: 52 },
      coffee: { good: true, hp: 1, w: 54, h: 48 },
      sweet: { good: true, hp: 1, w: 58, h: 48 },
      cake: { good: true, hp: 1, w: 58, h: 48 }
    } satisfies Record<ItemKind, { good: boolean; hp: number; w: number; h: number }>;
    return specs[kind];
  }

  private createItemIcon(kind: ItemKind) {
    const icon = this.add.container(0, 0);
    if (kind === "exam") {
      const g = this.add.graphics();
      g.fillStyle(0xf7f2df, 1);
      g.fillRoundedRect(-22, -27, 44, 54, 5);
      g.fillStyle(0xded6bd, 1);
      g.fillTriangle(10, -27, 22, -27, 22, -15);
      g.lineStyle(3, 0xff596d, 1);
      g.lineBetween(-10, -7, 10, 13);
      g.lineBetween(10, -7, -10, 13);
      g.lineStyle(2, 0x7c7f8a, 0.65);
      g.lineBetween(-12, -17, 5, -17);
      g.lineBetween(-12, 21, 12, 21);
      icon.add(g);
      return icon;
    }
    if (kind === "mail") {
      const g = this.add.graphics();
      g.fillStyle(0xffffff, 1);
      g.fillRoundedRect(-27, -18, 54, 36, 5);
      g.lineStyle(3, 0xff596d, 1);
      g.strokeRoundedRect(-27, -18, 54, 36, 5);
      g.lineBetween(-24, -15, 0, 4);
      g.lineBetween(24, -15, 0, 4);
      g.lineBetween(-24, 16, -5, 0);
      g.lineBetween(24, 16, 5, 0);
      icon.add(g);
      icon.add(this.add.text(0, 2, "@", {
        color: "#cf1f36",
        fontFamily: "sans-serif",
        fontSize: "20px",
        fontStyle: "900"
      }).setOrigin(0.5));
      return icon;
    }
    if (kind === "pdf") {
      const g = this.add.graphics();
      g.fillStyle(0xf7f2df, 1);
      g.fillRoundedRect(-28, -32, 56, 64, 5);
      g.fillStyle(0xff596d, 1);
      g.fillRoundedRect(-21, -2, 42, 22, 4);
      g.fillStyle(0xded6bd, 1);
      g.fillTriangle(12, -32, 28, -32, 28, -16);
      g.lineStyle(2, 0x7c7f8a, 0.5);
      g.lineBetween(-16, -19, 8, -19);
      g.lineBetween(-16, 25, 16, 25);
      icon.add(g);
      icon.add(this.add.text(0, 9, "PDF", {
        color: "#ffffff",
        fontFamily: "sans-serif",
        fontSize: "14px",
        fontStyle: "900"
      }).setOrigin(0.5));
      return icon;
    }
    if (kind === "weights") {
      const g = this.add.graphics();
      g.lineStyle(7, 0xd6d9e4, 1);
      g.lineBetween(-21, 0, 21, 0);
      g.fillStyle(0x313746, 1);
      g.fillRoundedRect(-34, -15, 12, 30, 4);
      g.fillRoundedRect(-46, -10, 10, 20, 4);
      g.fillRoundedRect(22, -15, 12, 30, 4);
      g.fillRoundedRect(36, -10, 10, 20, 4);
      g.lineStyle(3, 0xff596d, 1);
      g.strokeRoundedRect(-49, -18, 98, 36, 8);
      icon.add(g);
      return icon;
    }
    const emoji = kind === "coffee" ? "☕" : kind === "sweet" ? "🍩" : "🍰";
    const back = this.add.circle(0, 0, 29, 0xffffff, 0.94);
    back.setStrokeStyle(3, 0x7dffb0, 1);
    const text = this.add.text(0, 1, emoji, {
      fontFamily: "Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji, sans-serif",
      fontSize: "31px"
    }).setOrigin(0.5);
    icon.add([back, text]);
    return icon;
  }

  private hitItem(shot: Shot, item: FallingItem) {
    if (!item.activeItem) return;
    this.bullets.killAndHide(shot);
    shot.body.enable = false;
    if (item.good) {
      this.goodDestroyed += 1;
      this.damagePatience(gameConfig.gameplay.goodItemPenalty, true);
      this.floatMessage(this.goodHitMessage(item.kind), item.x, item.y, "#ff9aa8");
      this.flashAt(item.x, item.y, 0xff596d);
      this.disableItem(item);
      return;
    }
    item.hp -= 1;
    this.flashAt(item.x, item.y, 0xffe066);
    if (item.hp <= 0) {
      this.badDestroyed += 1;
      this.score += item.kind === "pdf" ? 90 : 50;
      this.floatMessage(this.badDestroyedMessage(item.kind), item.x, item.y, "#fff6c7");
      this.disableItem(item);
      this.playTone(160, 0.09, "sawtooth", 0.08);
    }
  }

  private playerHitByItem(item: FallingItem) {
    if (!item.activeItem || this.time.now < this.invulnerableUntil) return;
    if (item.good) {
      this.itemReachedBottom(item);
      return;
    }
    this.damagePatience(gameConfig.gameplay.directHitPenalty, true);
    this.floatMessage("Respira, Gema", this.player.x, this.player.y - 45, "#ffccd2");
    this.disableItem(item);
  }

  private playerHitByBossShot(shot: BossShot) {
    if (this.time.now < this.invulnerableUntil) return;
    this.bossBullets.killAndHide(shot);
    shot.body.enable = false;
    this.damagePatience(gameConfig.gameplay.bossHitPenalty, true);
    this.floatMessage("Ataque administrativo", this.player.x, this.player.y - 50, "#ffccd2");
  }

  private itemReachedBottom(item: FallingItem) {
    if (!item.activeItem) return;
    if (item.good) {
      this.activateBonus(item.kind);
    } else {
      this.damagePatience(gameConfig.gameplay.badItemMissPenalty, false);
      this.floatMessage("Se ha colado", item.x, H - 78, "#ffccd2");
    }
    this.disableItem(item);
  }

  private disableItem(item: FallingItem) {
    item.activeItem = false;
    item.body.enable = false;
    this.items.killAndHide(item);
  }

  private activateBonus(kind: ItemKind) {
    if (kind === "coffee") {
      this.rapidUntil = this.time.now + gameConfig.gameplay.rapidFireDurationMs;
      this.resetFireTimer();
      this.floatMessage("Cafe protegido", W / 2, H - 140, "#8effb6");
    } else if (kind === "sweet") {
      this.doubleUntil = this.time.now + gameConfig.gameplay.doubleShotDurationMs;
      this.floatMessage("Dulce protegido", W / 2, H - 140, "#8effb6");
    } else {
      this.patience = Math.min(gameConfig.gameplay.maxPatience, this.patience + 10);
      this.floatMessage("Paciencia recuperada", W / 2, H - 140, "#8effb6");
    }
    this.score += 35;
    this.treatsProtected += kind === "coffee" || kind === "sweet" ? 1 : 0;
    this.playTone(660, 0.08, "sine", 0.08);
  }

  private damagePatience(amount: number, shake: boolean) {
    this.patience = Math.max(0, this.patience - amount);
    this.invulnerableUntil = this.time.now + 850;
    this.tweens.add({ targets: this.hud.patienceBg, alpha: 0.35, yoyo: true, repeat: 3, duration: 80 });
    if (shake) this.cameras.main.shake(110, 0.004);
    this.playTone(90, 0.08, "triangle", 0.08);
    if (this.patience <= 0 && this.state !== "resetting") this.resetPatience();
  }

  private resetPatience() {
    this.state = "resetting";
    this.score = Math.max(0, this.score - 80);
    this.showCenterNotice(gameConfig.messages.patienceEmpty, 1200);
    this.items.children.each((child) => {
      const item = child as FallingItem;
      if (item.activeItem && !item.good && item.y > H * 0.45) this.disableItem(item);
      return true;
    });
    this.time.delayedCall(1200, () => {
      this.patience = 50;
      this.invulnerableUntil = this.time.now + 2000;
      this.state = this.boss ? "boss" : "playing";
    });
  }

  private startBoss() {
    this.state = "boss";
    this.spawnTimer?.remove(false);
    this.items.children.each((child) => {
      const item = child as FallingItem;
      if ((item as FallingItem).activeItem) this.tweens.add({ targets: item, y: H + 80, alpha: 0, duration: 650, onComplete: () => this.disableItem(item as FallingItem) });
      return true;
    });
    this.showCenterNotice(["JEFE FINAL", "UCAM"], 1400);
    this.hud.bossBarBg.setVisible(true);
    this.hud.bossBarFill.setVisible(true);
    this.hud.bossText.setVisible(true).setText("UCAM");
    this.boss = this.add.container(W / 2, -62) as BossContainer;
    const plate = this.add.rectangle(0, 0, 144, 82, 0xffffff, 0.92).setStrokeStyle(4, 0xff596d);
    const logo = this.add.image(0, 0, "ucam-logo").setDisplaySize(126, 58);
    this.boss.add([plate, logo]);
    this.boss.logo = logo;
    this.boss.hp = gameConfig.boss.health;
    this.boss.maxHp = gameConfig.boss.health;
    this.boss.direction = 1;
    this.physics.add.existing(this.boss);
    this.boss.body.setSize(132, 68);
    this.boss.body.setOffset(-66, -34);
    this.tweens.add({
      targets: this.boss,
      y: 126,
      duration: 900,
      ease: "Back.Out"
    });
    this.physics.add.overlap(this.bullets, this.boss, (shot) => this.hitBoss(shot as Shot));
    this.bossFireTimer = this.time.addEvent({ delay: 820, loop: true, callback: () => this.spawnBossShot() });
    this.bossExtraTimer = this.time.addEvent({
      delay: 2700,
      loop: true,
      callback: () => this.spawnFallingItem(Phaser.Math.RND.pick(["exam", "mail", "pdf", "weights"]))
    });
    this.playTone(220, 0.18, "sawtooth", 0.08);
  }

  private hitBoss(shot: Shot) {
    if (!this.boss || this.state !== "boss") return;
    this.bullets.killAndHide(shot);
    shot.body.enable = false;
    this.boss.hp -= this.time.now < this.doubleUntil ? 3.2 : 2.2;
    this.boss.logo.setTintFill(0xffccd2);
    this.time.delayedCall(50, () => this.boss?.logo.clearTint());
    if (this.boss.hp <= 0) this.win();
  }

  private spawnBossShot() {
    if (!this.boss || this.state !== "boss") return;
    const shot = this.acquireBossShot();
    shot.setActive(true).setVisible(true).setPosition(this.boss.x, this.boss.y + 48);
    shot.body.enable = true;
    shot.body.setSize(18, 22);
    shot.body.setVelocity(Phaser.Math.Between(-35, 35), 250);
  }

  private createBossShot(): BossShot {
    const shot = this.add.ellipse(0, 0, 18, 22, 0xff596d, 1) as BossShot;
    this.physics.add.existing(shot);
    this.bossBullets.add(shot);
    return shot;
  }

  private acquireBossShot(): BossShot {
    return (this.bossBullets.getFirstDead(false) as BossShot | null) ?? this.createBossShot();
  }

  private win() {
    if (!this.boss) return;
    this.state = "victory";
    this.clearTimers();
    this.bossBullets.clear(true, true);
    this.items.clear(true, true);
    this.score += 500;
    for (let i = 0; i < 42; i += 1) {
      const confetti = this.add.rectangle(this.boss.x, this.boss.y, 6, 10, Phaser.Math.RND.pick([0xffe066, 0x64df8a, 0x90f1ff, 0xff596d]), 1);
      this.tweens.add({
        targets: confetti,
        x: confetti.x + Phaser.Math.Between(-160, 160),
        y: confetti.y + Phaser.Math.Between(90, 310),
        angle: Phaser.Math.Between(-260, 260),
        alpha: 0,
        duration: Phaser.Math.Between(900, 1500),
        onComplete: () => confetti.destroy()
      });
    }
    this.tweens.add({
      targets: this.boss,
      scale: 0,
      alpha: 0,
      angle: 18,
      duration: 650,
      onComplete: () => {
        this.boss?.destroy();
        this.boss = undefined;
        this.hooks.onVictory({
          score: this.score,
          badDestroyed: this.badDestroyed,
          treatsProtected: this.treatsProtected,
          goodDestroyed: this.goodDestroyed
        });
      }
    });
    this.playTone(740, 0.22, "sine", 0.1);
  }

  private floatMessage(text: string, x: number, y: number, color: string) {
    while (this.floatingMessages.length > 1) this.floatingMessages.shift()?.destroy();
    const message = this.add.text(Phaser.Math.Clamp(x, 72, W - 72), Phaser.Math.Clamp(y, 82, H - 130), text, {
      color,
      fontFamily: "sans-serif",
      fontSize: "13px",
      fontStyle: "800",
      align: "center",
      stroke: "#10121a",
      strokeThickness: 4,
      wordWrap: { width: 145 }
    }).setOrigin(0.5).setDepth(30);
    this.floatingMessages.push(message);
    this.tweens.add({
      targets: message,
      y: message.y - 24,
      alpha: 0,
      duration: 820,
      onComplete: () => {
        this.floatingMessages = this.floatingMessages.filter((item) => item !== message);
        message.destroy();
      }
    });
  }

  private showCenterNotice(lines: readonly string[], duration: number) {
    const text = this.add.text(W / 2, H * 0.42, lines.join("\n"), {
      color: "#fff6c7",
      fontFamily: "sans-serif",
      fontSize: "25px",
      fontStyle: "900",
      align: "center",
      stroke: "#10121a",
      strokeThickness: 6
    }).setOrigin(0.5).setDepth(40);
    this.tweens.add({ targets: text, alpha: 0, y: text.y - 16, delay: duration, duration: 320, onComplete: () => text.destroy() });
  }

  private flashAt(x: number, y: number, color: number) {
    const flash = this.add.circle(x, y, 8, color, 0.65).setDepth(16);
    this.tweens.add({ targets: flash, scale: 3.6, alpha: 0, duration: 220, onComplete: () => flash.destroy() });
  }

  private badDestroyedMessage(kind: ItemKind) {
    if (kind === "exam") return "Examen eliminado";
    if (kind === "mail") return "Correo ignorado";
    if (kind === "weights") return "Pesas evitadas";
    return "PDF cerrado";
  }

  private goodHitMessage(kind: ItemKind) {
    if (kind === "coffee") return "Era cafe";
    if (kind === "sweet") return "Dulce desperdiciado";
    return "Eso ayudaba";
  }

  private playTone(frequency: number, duration: number, type: OscillatorType, volume: number) {
    if (!this.soundEnabled || !this.hooks.onSoundRequest()) return;
    const browserWindow = globalThis as typeof globalThis & {
      webkitAudioContext?: typeof AudioContext;
    };
    const AudioContextClass = browserWindow.AudioContext || browserWindow.webkitAudioContext;
    if (!AudioContextClass) return;
    const context = new AudioContextClass();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = frequency;
    oscillator.type = type;
    gain.gain.value = volume;
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + duration);
    oscillator.onended = () => context.close();
  }
}
