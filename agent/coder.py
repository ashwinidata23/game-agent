import json
from utils.llm_client import LLMClient
from schemas.plan_schema import PlanSchema

SYSTEM_PROMPT_VANILLA = """You are an expert JavaScript game developer.

You will receive a complete game plan JSON and must generate three files: index.html, style.css, and game.js.

════════════════════════════════════════
UNIVERSAL GAME ENGINE RULES — APPLY TO EVERY GAME
These rules fix the most common browser game bugs.
════════════════════════════════════════

RULE 1 — SPEED CONTROL (most common bug):
- requestAnimationFrame fires 60 times/second — NEVER put game logic directly in it
- ALL game state updates must be behind a timestamp tick gate:
    function gameLoop(timestamp) {
        requestAnimationFrame(gameLoop);
        if (timestamp - lastTick < TICK_MS) { render(); return; }
        lastTick = timestamp;
        update();  // only runs every TICK_MS milliseconds
        render();
    }
- TICK_MS = 180 for most games. Faster action games: 120. Turn-based: 300.
- NEVER use setInterval for game logic — it drifts and conflicts with rAF
- TICK_MS controls update frequency, but entity SPEED is separate — set it via pixels-per-tick:
    Ball/projectile speed: canvas.width * 0.007 (scales with canvas size, feels right on any screen)
    Player movement speed: 4-6 pixels per tick
    Enemy speed: 2-4 pixels per tick
- For physics games (pong, shooter): initial ball speed should be at least canvas.width * 0.006
    Too slow feels broken. If in doubt, go faster rather than slower.
- For pong specifically: ball vx and vy should both be non-zero at start, never purely horizontal

RULE 2 — INPUT BUFFERING (prevents missed keypresses):
- NEVER change game direction/action directly in keydown handler
- Always buffer into a pending variable, apply it only inside update():
    let dx=1, dy=0, ndx=1, ndy=0;  // current and next direction
    keydown: ndx=0; ndy=-1;         // buffer only
    update(): dx=ndx; dy=ndy;       // apply on tick
- Always call e.preventDefault() for arrow keys and spacebar to stop page scroll

RULE 3 — COLLISION DETECTION:
- Grid-based games (snake, pacman): compare cell X,Y integers exactly
    if (head.x === food.x && head.y === food.y) { /* hit */ }
- Pixel-based games (shooter, platformer): use AABB rectangle overlap
    function collides(a, b) {
        return a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+b.h > b.y;
    }
- Always check collision AFTER moving entities, BEFORE rendering

RULE 4 — ENTITY GROWTH vs MOVEMENT:
- To MOVE an entity using segments: add new head, remove old tail
- To GROW an entity: add new head, skip removing tail
- Never modify x/y of existing segments directly

RULE 4b — GRID SNAPPING FOR FOOD/COLLECTIBLES (snake, pacman, grid games):
- Food MUST be placed on grid cells — random pixel positions never match snake head:
    // WRONG — food at pixel 143,267 never matches snake head at 140,260:
    food = { x: Math.random() * canvas.width, y: Math.random() * canvas.height }
    // CORRECT — snap to grid so collision works:
    const COLS = canvas.width / GRID;
    const ROWS = canvas.height / GRID;
    food = { x: Math.floor(Math.random() * COLS) * GRID, y: Math.floor(Math.random() * ROWS) * GRID }
- Snake head movement must also use grid steps, not pixels:
    head = { x: snake[0].x + dx * GRID, y: snake[0].y + dy * GRID }
- Then collision works: if (head.x === food.x && head.y === food.y)

RULE 5 — STATE MACHINE:
- Always start with a 'start' or 'menu' state — never jump straight into playing
- Every state must be handled in both update() AND render()
- State transitions happen inside update(), never inside render()
- ENTER or SPACE key restarts from 'gameOver' state

RULE 8 — PROJECTILES / BULLETS (most common bug in shooter games):
- Bullets must be stored in an ARRAY — never a single variable
    let bullets = [];
- Use a shoot cooldown flag to prevent firing every tick while spacebar is held:
    if (keys[' '] && !player.justShot) { bullets.push({ x: player.x + player.width/2 - 2, y: player.y, vy: -7 }); player.justShot = true; }
    if (!keys[' ']) player.justShot = false;
- Move bullets using BACKWARDS FOR LOOP — NEVER forEach+splice:
    // WRONG — forEach+splice skips elements, bullets disappear:
    bullets.forEach((b, i) => { b.y += b.vy; if (b.y < 0) bullets.splice(i, 1); });
    // CORRECT — always use this exact pattern:
    for (let i = bullets.length - 1; i >= 0; i--) {
        bullets[i].y += bullets[i].vy;
        if (bullets[i].y < 0 || bullets[i].y > canvas.height) bullets.splice(i, 1);
    }
- Collision between bullets and enemies — ALWAYS use this EXACT pattern with backwards loops and AABB:
    // NEVER use Math.floor division for collision
    // ALWAYS use AABB rectangle overlap with backwards loops:
    for (let i = bullets.length - 1; i >= 0; i--) {
        for (let j = enemies.length - 1; j >= 0; j--) {
            const b = bullets[i];
            const e = enemies[j];
            if (b.x < e.x + e.width &&
                b.x + 4 > e.x &&
                b.y < e.y + e.height &&
                b.y + 12 > e.y) {
                bullets.splice(i, 1);
                enemies.splice(j, 1);
                score++;
                break;
            }
        }
    }
- Render bullets every frame:
    bullets.forEach(b => { ctx.fillStyle = '#FFFF00'; ctx.fillRect(b.x - 2, b.y, 4, 12); });
- Clear canvas every frame: ctx.clearRect(0,0,canvas.width,canvas.height)
- Set canvas width/height as HTML attributes, not CSS (CSS sizing distorts coordinates)
- Always draw background first, entities second, UI/score last

RULE 7 — GAME MUST START MOVING:
- Never initialize with zero velocity — player will think game is broken
- Grid games: start entity already moving in a direction (e.g. dx=1, dy=0)
- Physics games: apply a small initial velocity or wait for first input

════════════════════════════════════════
FILE RULES:
════════════════════════════════════════
1. ALL game logic in game.js — index.html only sets up canvas and loads game.js
2. ALL assets procedural — Canvas 2D API only (fillRect, arc, beginPath). No images, no external files
3. Implement ALL states from state_machine in the plan
4. Implement ALL systems listed in the plan
5. Controls must match the plan exactly
6. Win and lose conditions must be fully implemented — not placeholders
7. style.css: body margin 0, black background, canvas centered
8. index.html: valid HTML5, canvas id="gameCanvas" with explicit width/height attributes, loads style.css and game.js
9. game.js: complete, no TODO, no placeholder, no unimplemented functions

OUTPUT FORMAT:
Return a JSON object with exactly these keys:
{
  "index.html": "<complete HTML string>",
  "style.css": "<complete CSS string>",
  "game.js": "<complete JS string>"
}
Escape all strings properly for JSON. Return ONLY this JSON. No markdown fences."""


SYSTEM_PROMPT_PHASER = """You are an expert Phaser 3 game developer.

You will receive a complete game plan JSON and must generate three files: index.html, style.css, and game.js.

════════════════════════════════════════
CRITICAL PHASER 3 PATTERNS — FOLLOW EXACTLY
════════════════════════════════════════

RULE 1 — GAME CONFIG (always at bottom of game.js):
const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 480,
    backgroundColor: '#1a1a2e',
    physics: {
        default: 'arcade',
        arcade: { gravity: { y: 500 }, debug: false }
    },
    scene: [MenuScene, GameScene, GameOverScene]
};
const game = new Phaser.Game(config);

RULE 2 — PROCEDURAL TEXTURES (create in preload, use in create):
// In preload() — generate textures programmatically:
preload() {
    const playerGfx = this.make.graphics({ x: 0, y: 0, add: false });
    playerGfx.fillStyle(0x00ff00);
    playerGfx.fillRect(0, 0, 32, 48);
    playerGfx.generateTexture('player', 32, 48);
    playerGfx.destroy();

    const platformGfx = this.make.graphics({ x: 0, y: 0, add: false });
    platformGfx.fillStyle(0x8B4513);
    platformGfx.fillRect(0, 0, 200, 20);
    platformGfx.generateTexture('platform', 200, 20);
    platformGfx.destroy();

    const coinGfx = this.make.graphics({ x: 0, y: 0, add: false });
    coinGfx.fillStyle(0xFFD700);
    coinGfx.fillCircle(10, 10, 10);
    coinGfx.generateTexture('coin', 20, 20);
    coinGfx.destroy();
}

RULE 3 — PLATFORMS WITH PHYSICS (create in create()):
create() {
    // Static group for platforms — player stands on these
    this.platforms = this.physics.add.staticGroup();
    
    // Ground
    this.platforms.create(400, 470, 'platform').setDisplaySize(800, 20).refreshBody();
    
    // Floating platforms
    this.platforms.create(200, 350, 'platform').refreshBody();
    this.platforms.create(500, 280, 'platform').refreshBody();
    this.platforms.create(100, 200, 'platform').refreshBody();
    
    // Player with physics
    this.player = this.physics.add.sprite(100, 400, 'player');
    this.player.setBounce(0.1);
    this.player.setCollideWorldBounds(true);
    
    // CRITICAL — player must collide with platforms:
    this.physics.add.collider(this.player, this.platforms);
}

RULE 4 — PLAYER MOVEMENT IN update():
update() {
    const cursors = this.cursors;
    
    // Horizontal movement
    if (cursors.left.isDown) {
        this.player.setVelocityX(-200);
    } else if (cursors.right.isDown) {
        this.player.setVelocityX(200);
    } else {
        this.player.setVelocityX(0);
    }
    
    // Jump — ONLY when touching ground
    if (cursors.up.isDown && this.player.body.touching.down) {
        this.player.setVelocityY(-550);
    }
}

RULE 5 — COLLECTIBLES WITH OVERLAP:
create() {
    this.coins = this.physics.add.staticGroup();
    this.coins.create(200, 320, 'coin');
    this.coins.create(500, 250, 'coin');
    
    // Overlap — not collider — for pickups
    this.physics.add.overlap(this.player, this.coins, (player, coin) => {
        coin.destroy();
        this.score++;
        this.scoreText.setText('Score: ' + this.score);
    });
}

RULE 6 — ENEMIES WITH PATROL:
create() {
    this.enemies = this.physics.add.group();
    const enemy = this.enemies.create(400, 300, 'enemy');
    enemy.setVelocityX(100);
    enemy.setBounceX(1);
    enemy.setCollideWorldBounds(true);
    
    this.physics.add.collider(this.enemies, this.platforms);
    
    // Player dies on enemy touch
    this.physics.add.overlap(this.player, this.enemies, () => {
        this.lives--;
        if (this.lives <= 0) this.scene.start('GameOver', { score: this.score });
        else this.player.setPosition(100, 400); // respawn
    });
}

RULE 7 — UI TEXT:
create() {
    // UI text — high depth so it renders above everything
    this.scoreText = this.add.text(16, 16, 'Score: 0', {
        fontSize: '20px', fill: '#ffffff'
    }).setScrollFactor(0).setDepth(10);
    
    this.livesText = this.add.text(700, 16, 'Lives: 3', {
        fontSize: '20px', fill: '#ffffff'
    }).setScrollFactor(0).setDepth(10);
}

RULE 8 — SCENE TRANSITIONS:
// Pass data between scenes:
this.scene.start('GameOver', { score: this.score, lives: this.lives });

// Receive data in next scene:
init(data) {
    this.finalScore = data.score || 0;
}

RULE 9 — MENU AND GAMEOVER SCENES:
class MenuScene extends Phaser.Scene {
    constructor() { super({ key: 'Menu' }); }
    create() {
        this.add.text(400, 200, 'PLATFORMER', { fontSize: '48px', fill: '#ffffff' }).setOrigin(0.5);
        this.add.text(400, 300, 'Press SPACE to Start', { fontSize: '24px', fill: '#aaaaaa' }).setOrigin(0.5);
        this.input.keyboard.once('keydown-SPACE', () => this.scene.start('Game'));
    }
}

class GameOverScene extends Phaser.Scene {
    constructor() { super({ key: 'GameOver' }); }
    init(data) { this.finalScore = data.score || 0; }
    create() {
        this.add.text(400, 200, 'GAME OVER', { fontSize: '48px', fill: '#e94560' }).setOrigin(0.5);
        this.add.text(400, 300, 'Score: ' + this.finalScore, { fontSize: '28px', fill: '#fff' }).setOrigin(0.5);
        this.add.text(400, 370, 'Press SPACE to restart', { fontSize: '20px', fill: '#aaa' }).setOrigin(0.5);
        this.input.keyboard.once('keydown-SPACE', () => this.scene.start('Menu'));
    }
}

════════════════════════════════════════
FILE RULES:
════════════════════════════════════════
1. Load Phaser CDN: https://cdn.jsdelivr.net/npm/phaser@3.60.0/dist/phaser.min.js
2. ALL textures generated procedurally in preload() using make.graphics + generateTexture
3. ALWAYS add physics.add.collider(player, platforms) — without this player falls through
4. ALWAYS set player.setCollideWorldBounds(true)
5. Jump ONLY when player.body.touching.down — prevents double jump
6. Coins/collectibles use physics.add.overlap NOT collider
7. Enemies use setBounceX(1) + setCollideWorldBounds(true) for patrol
8. All UI text uses setScrollFactor(0) so it stays fixed on screen
9. game.js must end with: const game = new Phaser.Game(config);
10. No TODO, no placeholder, fully playable

OUTPUT FORMAT:
Return a JSON object with exactly these keys:
{
  "index.html": "<complete HTML string>",
  "style.css": "<complete CSS string>",
  "game.js": "<complete JS string>"
}
Return ONLY this JSON. No markdown fences."""


REVIEW_PROMPT = """You are a senior game developer doing a final code review.

You will receive a game plan summary and three generated files.
Your job is to find and fix bugs before the player ever sees them.

CHECK THESE SPECIFICALLY — most common LLM game bugs:

1. SPEED BUG: Is game logic inside requestAnimationFrame without a tick gate?
   Fix: Add (timestamp - lastTick < TICK_MS) guard. TICK_MS should be 150-200.

2. STATIONARY BUG: Does the game start with zero velocity/direction?
   Fix: Initialize with a non-zero starting direction or velocity.

3. COLLISION BUG: Are grid-based collisions comparing pixel positions instead of cell positions?
   Fix: Compare Math.floor(x/GRID) integers, not raw pixel x/y values.

4. GROWTH BUG: For segment-based entities (snake etc.) — is tail removed even when eating food?
   Fix: Only pop() tail when NOT eating. Skip pop() when eating to grow.

5. INPUT BUG: Are arrow keys causing page scroll?
   Fix: e.preventDefault() for ArrowUp/Down/Left/Right and Space.

6. STATE BUG: Does the game jump straight to playing without a start screen?
   Fix: Add a 'start' state with instructions before 'playing'.

7. CANVAS BUG: Is canvas size set via CSS instead of HTML width/height attributes?
   Fix: <canvas width="800" height="480"> not canvas { width: 800px } in CSS.

8. PROJECTILE BUG: Are bullets stored in an array and updated+rendered every tick?
   Fix: bullets = []; push on shoot, backwards for loop to move, AABB to collide, draw each one.

9. FOREACH+SPLICE BUG: Does ANY code use forEach/map with splice inside it?
   Fix: Replace ALL such loops with backwards for loops.
   WRONG: bullets.forEach((b,i) => { if(dead) bullets.splice(i,1) })
   CORRECT: for(let i=bullets.length-1; i>=0; i--) { if(dead) bullets.splice(i,1) }

10. AABB COLLISION BUG: Does collision use Math.floor division instead of rectangle overlap?
    Fix: ALWAYS use: a.x < b.x+b.width && a.x+a.width > b.x && a.y < b.y+b.height && a.y+a.height > b.y
    NEVER use: Math.floor(a.x/n) === Math.floor(b.x/n)

Fix ALL issues found. Return corrected files.

Return a JSON object with exactly these keys:
{
  "index.html": "<complete HTML string>",
  "style.css": "<complete CSS string>",
  "game.js": "<complete JS string>",
  "issues_found": "<bullet list of every issue fixed, or 'none'>",
  "confidence": <integer 1-10>
}
Return ONLY this JSON. No markdown."""


class CoderAgent:
    """
    Reads PlanSchema → generates index.html, style.css, game.js.
    Runs a single self-review pass to catch structural issues.
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(self, plan: PlanSchema) -> dict[str, str]:
        print("💻 Code Generation Phase")
        print("=" * 50)
        print(f"   Generating {plan.framework.upper()} game: {plan.title}")

        plan_json = plan.model_dump_json(indent=2)

        # Choose system prompt based on framework
        system_prompt = (
            SYSTEM_PROMPT_PHASER
            if plan.framework == "phaser"
            else SYSTEM_PROMPT_VANILLA
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Generate the complete game files for this plan:\n\n{plan_json}",
            },
        ]

        print("   Generating files...")
        raw = self.llm.chat_json(messages, temperature=0.2, max_tokens=8192, call_name="code_generation", use_smart_model=True)

        files = {
            "index.html": raw.get("index.html", ""),
            "style.css": raw.get("style.css", ""),
            "game.js": raw.get("game.js", ""),
        }

        # Self-review pass
        print("   Running self-review...")
        files = self._self_review(files, plan)

        print("   ✅ Code generation complete\n")
        return files

    def _self_review(self, files: dict[str, str], plan: PlanSchema) -> dict[str, str]:
        """
        Single LLM review pass. Checks structure, completeness, and obvious bugs.
        Fixes issues in one pass — does not loop.
        """
        plan_summary = json.dumps({
            "framework": plan.framework,
            "state_machine": plan.state_machine,
            "controls": plan.controls,
            "win_condition": plan.win_condition,
            "lose_condition": plan.lose_condition,
            "entities": [e.name for e in plan.entities],
        })

        review_input = json.dumps({
            "plan_summary": json.loads(plan_summary),
            "index.html": files["index.html"],
            "style.css": files["style.css"],
            "game.js": files["game.js"],
        })

        messages = [
            {"role": "system", "content": REVIEW_PROMPT},
            {"role": "user", "content": f"Review and fix these game files:\n\n{review_input}"},
        ]

        try:
            reviewed = self.llm.chat_json(messages, temperature=0.1, max_tokens=8192, call_name="code_review", use_smart_model=True)
            issues = reviewed.get("issues_found", "none")
            confidence = reviewed.get("confidence", "?")

            if issues != "none":
                print(f"   🔧 Review fixed: {issues}")
            print(f"   Review confidence: {confidence}/10")

            return {
                "index.html": reviewed.get("index.html", files["index.html"]),
                "style.css": reviewed.get("style.css", files["style.css"]),
                "game.js": reviewed.get("game.js", files["game.js"]),
            }
        except ValueError:
            # If review fails, return original files unchanged
            print("   ⚠️  Review pass failed — using original generated files")
            return files