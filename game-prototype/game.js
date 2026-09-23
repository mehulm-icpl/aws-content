const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const scoreEl = document.getElementById('score');
const healthEl = document.getElementById('health');
const timeEl = document.getElementById('time');
const startButton = document.getElementById('startButton');

const game = {
  width: canvas.width,
  height: canvas.height,
  running: false,
  over: false,
  win: false,
  score: 0,
  totalScore: 0,
  round: 1,
  maxRounds: 3,
  targetScore: 8,
  timeLeft: 45,
  health: 100,
  lastTime: 0,
  message: 'Collect the cores and stay away from drones.'
};

const keys = {
  ArrowUp: false,
  ArrowDown: false,
  ArrowLeft: false,
  ArrowRight: false,
  w: false,
  a: false,
  s: false,
  d: false
};

const player = {
  x: 110,
  y: canvas.height / 2,
  radius: 16,
  speed: 260,
  invulnerable: 0
};

const pickups = [];
const drones = [];

function resetGame() {
  game.running = true;
  game.over = false;
  game.win = false;
  game.score = 0;
  game.timeLeft = Math.max(25, 45 - (game.round - 1) * 5);
  game.health = 100;
  player.x = 110;
  player.y = canvas.height / 2;
  player.invulnerable = 0;

  pickups.length = 0;
  drones.length = 0;

  const target = Math.min(game.targetScore + game.round - 1, 12);
  for (let i = 0; i < target; i += 1) {
    pickups.push({
      x: 90 + Math.random() * (canvas.width - 180),
      y: 60 + Math.random() * (canvas.height - 120),
      radius: 9,
      hue: i % 2 === 0 ? 162 : 45
    });
  }

  const droneCount = 5 + game.round;
  for (let i = 0; i < droneCount; i += 1) {
    drones.push({
      x: canvas.width * (0.7 + Math.random() * 0.25),
      y: 60 + Math.random() * (canvas.height - 120),
      radius: 14,
      speed: 90 + Math.random() * 70 + game.round * 8,
      dx: (Math.random() > 0.5 ? 1 : -1) * (0.6 + Math.random() * 0.8),
      dy: (Math.random() > 0.5 ? 1 : -1) * (0.6 + Math.random() * 0.8)
    });
  }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function updatePlayer(delta) {
  let moveX = 0;
  let moveY = 0;

  if (keys.ArrowLeft || keys.a) moveX -= 1;
  if (keys.ArrowRight || keys.d) moveX += 1;
  if (keys.ArrowUp || keys.w) moveY -= 1;
  if (keys.ArrowDown || keys.s) moveY += 1;

  const length = Math.hypot(moveX, moveY) || 1;
  moveX /= length;
  moveY /= length;

  player.x += moveX * player.speed * delta;
  player.y += moveY * player.speed * delta;

  player.x = clamp(player.x, player.radius, canvas.width - player.radius);
  player.y = clamp(player.y, player.radius, canvas.height - player.radius);

  if (player.invulnerable > 0) {
    player.invulnerable = Math.max(0, player.invulnerable - delta);
  }
}

function updatePickups() {
  for (let i = pickups.length - 1; i >= 0; i -= 1) {
    const item = pickups[i];
    const dx = player.x - item.x;
    const dy = player.y - item.y;
    const distance = Math.hypot(dx, dy);

    if (distance < player.radius + item.radius + 4) {
      pickups.splice(i, 1);
      game.score += 1;
      scoreEl.textContent = game.score;
    }
  }
}

function updateDrones(delta) {
  for (const drone of drones) {
    const dx = player.x - drone.x;
    const dy = player.y - drone.y;
    const distance = Math.hypot(dx, dy) || 1;

    drone.x += (dx / distance) * drone.speed * delta;
    drone.y += (dy / distance) * drone.speed * delta;

    if (drone.x < 20 || drone.x > canvas.width - 20) {
      drone.dx *= -1;
    }
    if (drone.y < 20 || drone.y > canvas.height - 20) {
      drone.dy *= -1;
    }

    drone.x += drone.dx * drone.speed * 0.28 * delta;
    drone.y += drone.dy * drone.speed * 0.28 * delta;

    const closeEnough = Math.hypot(player.x - drone.x, player.y - drone.y) < player.radius + drone.radius + 2;
    if (closeEnough && player.invulnerable <= 0) {
      game.health = Math.max(0, game.health - 15);
      player.invulnerable = 1;
      healthEl.textContent = game.health;

      if (game.health <= 0) {
        endGame(false, 'Drone strike! The run is over.');
      }
    }
  }
}

function endGame(won, text) {
  game.running = false;
  game.over = true;
  game.win = won;
  game.message = text;

  if (won && game.round < game.maxRounds) {
    startButton.textContent = 'Next Round';
    return;
  }

  startButton.textContent = game.totalScore > 0 ? 'Play Again' : 'Start Run';
}

function advanceToNextRound() {
  if (game.round < game.maxRounds) {
    game.round += 1;
    game.totalScore += game.score;
    startButton.textContent = 'Start Round ' + game.round;
    game.running = false;
    game.over = true;
    game.win = false;
    game.message = 'Round ' + (game.round - 1) + ' complete! Ready for the next run?';
    return true;
  }

  game.totalScore += game.score;
  game.running = false;
  game.over = true;
  game.win = true;
  game.message = 'Campaign complete! Total score: ' + game.totalScore;
  startButton.textContent = 'Play Again';
  return false;
}

function updateGame(delta) {
  if (!game.running) return;

  game.timeLeft = Math.max(0, game.timeLeft - delta);
  timeEl.textContent = Math.ceil(game.timeLeft);

  updatePlayer(delta);
  updatePickups();
  updateDrones(delta);

  if (game.score >= Math.min(game.targetScore + game.round - 1, 12)) {
    game.totalScore += game.score;
    if (game.round >= game.maxRounds) {
      endGame(true, 'Campaign complete! Total score: ' + game.totalScore);
    } else {
      const nextLoop = advanceToNextRound();
      if (nextLoop) {
        game.totalScore = game.totalScore;
      }
    }
    return;
  }

  if (game.timeLeft <= 0) {
    game.totalScore += game.score;
    if (game.round >= game.maxRounds) {
      endGame(false, 'Campaign over. Final score: ' + game.totalScore);
    } else {
      advanceToNextRound();
    }
  }
}

function drawBackground() {
  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, '#0d1730');
  gradient.addColorStop(1, '#09111f');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.strokeStyle = 'rgba(99, 230, 255, 0.15)';
  ctx.lineWidth = 1;
  for (let x = 0; x < canvas.width; x += 40) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y < canvas.height; y += 40) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }
}

function drawPlayer() {
  ctx.beginPath();
  ctx.fillStyle = player.invulnerable > 0 && Math.floor(player.invulnerable * 8) % 2 === 0 ? '#ffffff' : '#63e6ff';
  ctx.arc(player.x, player.y, player.radius, 0, Math.PI * 2);
  ctx.fill();

  ctx.beginPath();
  ctx.fillStyle = '#d7faff';
  ctx.arc(player.x + 5, player.y - 4, 3, 0, Math.PI * 2);
  ctx.fill();
}

function drawPickups() {
  for (const item of pickups) {
    ctx.beginPath();
    ctx.fillStyle = `hsla(${item.hue}, 100%, 65%, 1)`;
    ctx.moveTo(item.x, item.y - item.radius);
    ctx.lineTo(item.x + item.radius * 0.7, item.y);
    ctx.lineTo(item.x, item.y + item.radius);
    ctx.lineTo(item.x - item.radius * 0.7, item.y);
    ctx.closePath();
    ctx.fill();
  }
}

function drawDrones() {
  for (const drone of drones) {
    ctx.beginPath();
    ctx.fillStyle = '#ff5c7a';
    ctx.arc(drone.x, drone.y, drone.radius, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.strokeStyle = '#ffd166';
    ctx.lineWidth = 2;
    ctx.moveTo(drone.x - 8, drone.y);
    ctx.lineTo(drone.x + 8, drone.y);
    ctx.moveTo(drone.x, drone.y - 8);
    ctx.lineTo(drone.x, drone.y + 8);
    ctx.stroke();
  }
}

function drawOverlay() {
  if (!game.running) {
    ctx.fillStyle = 'rgba(3, 8, 18, 0.55)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = '#eaf6ff';
    ctx.textAlign = 'center';
    ctx.font = 'bold 38px Arial';
    const title = game.win ? 'MISSION COMPLETE' : (game.round > 1 ? 'ROUND CLEAR' : 'RUN ENDED');
    ctx.fillText(title, canvas.width / 2, canvas.height / 2 - 10);

    ctx.font = '20px Arial';
    ctx.fillText(game.message, canvas.width / 2, canvas.height / 2 + 30);
  }
}

function drawHUDValues() {
  scoreEl.textContent = game.score + ' / ' + Math.min(game.targetScore + game.round - 1, 12);
  healthEl.textContent = game.health;
  timeEl.textContent = Math.ceil(game.timeLeft);
}

function tick(timestamp) {
  const delta = Math.min((timestamp - game.lastTime) / 1000 || 0.016, 0.035);
  game.lastTime = timestamp;

  updateGame(delta);
  drawBackground();
  drawPickups();
  drawDrones();
  drawPlayer();
  drawOverlay();
  drawHUDValues();

  requestAnimationFrame(tick);
}

window.addEventListener('keydown', (event) => {
  const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
  if (keys[key] !== undefined) {
    keys[key] = true;
  }
});

window.addEventListener('keyup', (event) => {
  const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
  if (keys[key] !== undefined) {
    keys[key] = false;
  }
});

startButton.addEventListener('click', () => {
  if (game.over && game.message.includes('Round') && !game.running) {
    game.over = false;
    game.running = true;
    resetGame();
    startButton.textContent = 'Running...';
    return;
  }

  if (game.over && game.message.includes('Campaign complete') && !game.running) {
    game.round = 1;
    game.totalScore = 0;
    game.score = 0;
    game.over = false;
    game.running = true;
    resetGame();
    startButton.textContent = 'Running...';
    return;
  }

  if (game.over && !game.running && game.win && game.round < game.maxRounds) {
    game.over = false;
    game.running = true;
    resetGame();
    startButton.textContent = 'Running...';
    return;
  }

  game.totalScore = 0;
  game.round = 1;
  resetGame();
  startButton.textContent = 'Running...';
});

game.totalScore = 0;
resetGame();
startButton.textContent = 'Start Round 1';
requestAnimationFrame(tick);
