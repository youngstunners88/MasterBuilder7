<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Echoes of the Vortex - 3D Ultimate Edition</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #000;
            color: #fff;
            font-family: Arial, sans-serif;
            overflow: hidden;
        }
        #game-container {
            width: 100vw;
            height: 100vh;
            position: relative;
        }
        #game-hud {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.7);
            padding: 10px;
            border-radius: 5px;
            font-size: 18px;
        }
        .main-menu {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.8);
            padding: 20px;
            border: 2px solid #fff;
            border-radius: 10px;
            text-align: center;
            width: 300px;
        }
        .main-menu input, .main-menu select, .main-menu button {
            margin: 10px 0;
            padding: 10px;
            width: 100%;
            box-sizing: border-box;
        }
        .pause-menu {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.8);
            padding: 20px;
            border: 2px solid #fff;
            border-radius: 10px;
            text-align: center;
            display: none;
        }
        .pause-menu button {
            margin: 10px 0;
            padding: 10px;
            width: 100%;
            box-sizing: border-box;
        }
        .certificate {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.9);
            padding: 20px;
            border: 2px solid #fff;
            border-radius: 10px;
            text-align: center;
            display: none;
        }
        .power-up-notification {
            position: absolute;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(255, 0, 0, 0.8);
            color: #fff;
            padding: 10px;
            border-radius: 5px;
            display: none;
        }
    </style>
</head>
<body>
    <div id="game-container">
        <div id="game-hud">
            <p id="score-text">Score: 0</p>
            <p id="timer-text">Time: 60</p>
            <p id="health-text">Health: 100</p>
            <p id="secrets-text">Secrets: 0</p>
        </div>
        <div class="main-menu" id="main-menu">
            <h2>Echoes of the Vortex - 3D</h2>
            <input type="text" id="player-name" placeholder="Your Name" required>
            <input type="number" id="player-age" placeholder="Your Age" required>
            <select id="english-level">
                <option value="Beginner">Beginner</option>
                <option value="Intermediate">Intermediate</option>
                <option value="Advanced">Advanced</option>
                <option value="Fluent">Fluent</option>
            </select>
            <select id="difficulty">
                <option value="Easy">Easy</option>
                <option value="Medium">Medium</option>
                <option value="Hard">Hard</option>
                <option value="Extreme">Extreme</option>
            </select>
            <button onclick="startGame()">Start Game</button>
            <p>Controls: W/A/S/D to move | Space to jump | Click to shoot | P to pause</p>
        </div>
        <div class="pause-menu" id="pause-menu">
            <h2>Paused</h2>
            <button onclick="resumeGame()">Resume</button>
            <button onclick="restartGame()">Restart</button>
            <button onclick="exitToMainMenu()">Main Menu</button>
        </div>
        <div class="certificate" id="certificate">
            <h2>Certificate of Completion</h2>
            <p id="cert-name">Name: </p>
            <p id="cert-age">Age: </p>
            <p id="cert-level">English Level: </p>
            <p id="cert-difficulty">Difficulty: </p>
            <p id="cert-score">Score: </p>
            <p id="cert-time">Time: </p>
            <p id="cert-secrets">Secrets Found: </p>
            <p id="cert-enemies">Enemies Defeated: </p>
            <button onclick="restartGame()">Play Again</button>
        </div>
        <div class="power-up-notification" id="power-up-notification">Power-up activated!</div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/cannon@0.6.2/build/cannon.min.js"></script>
    <script>
        // Game variables
        let scene, camera, renderer, playerModel, groundModel, world, playerBody;
        let score = 0, timeLeft = 60, health = 100, playerName = "Player", playerAge = 18, englishLevel = "Beginner", difficulty = "Easy";
        let enemiesDefeated = 0, secretsFound = 0, powerUpActive = false, isPaused = false, gameOver = false;
        let enemies = [], secrets = [], bullets = [];
        let lastTime = performance.now();
        let powerUpNotification;

        // Physics world setup with Cannon.js
        world = new CANNON.World();
        world.gravity.set(0, -9.82, 0);

        // Three.js scene setup
        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 5, 10);
        renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        document.getElementById('game-container').appendChild(renderer.domElement);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        scene.add(ambientLight);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
        directionalLight.position.set(0, 10, 0);
        scene.add(directionalLight);

        // Ground
        const groundGeometry = new THREE.PlaneGeometry(100, 100);
        const groundMaterial = new THREE.MeshBasicMaterial({ color: 0x555555 });
        groundModel = new THREE.Mesh(groundGeometry, groundMaterial);
        groundModel.rotation.x = -Math.PI / 2;
        scene.add(groundModel);
        const groundShape = new CANNON.Plane();
        const groundBody = new CANNON.Body({ mass: 0 });
        groundBody.addShape(groundShape);
        groundBody.quaternion.setFromEuler(-Math.PI / 2, 0, 0);
        world.addBody(groundBody);

        // Player
        const playerGeometry = new THREE.BoxGeometry(1, 1, 1);
        const playerMaterial = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
        playerModel = new THREE.Mesh(playerGeometry, playerMaterial);
        playerModel.position.y = 0.5;
        scene.add(playerModel);
        const playerShape = new CANNON.Box(new CANNON.Vec3(0.5, 0.5, 0.5));
        playerBody = new CANNON.Body({ mass: 1 });
        playerBody.addShape(playerShape);
        playerBody.position.set(0, 0.5, 0);
        world.addBody(playerBody);

        // Keyboard controls
        const keys = { w: false, a: false, s: false, d: false, space: false };
        document.addEventListener('keydown', (event) => {
            if (event.key === 'w') keys.w = true;
            if (event.key === 'a') keys.a = true;
            if (event.key === 's') keys.s = true;
            if (event.key === 'd') keys.d = true;
            if (event.key === ' ') keys.space = true;
            if (event.key === 'p' && !gameOver) togglePause();
        });
        document.addEventListener('keyup', (event) => {
            if (event.key === 'w') keys.w = false;
            if (event.key === 'a') keys.a = false;
            if (event.key === 's') keys.s = false;
            if (event.key === 'd') keys.d = false;
            if (event.key === ' ') keys.space = false;
        });

        // Mouse controls for shooting
        document.addEventListener('click', () => {
            if (!isPaused && !gameOver) shootBullet();
        });

        // Spawn enemies
        function spawnEnemy() {
            const enemyGeometry = new THREE.SphereGeometry(0.5, 32, 32);
            const enemyMaterial = new THREE.MeshBasicMaterial({ color: 0xff0000 });
            const enemyModel = new THREE.Mesh(enemyGeometry, enemyMaterial);
            const x = (Math.random() - 0.5) * 80;
            const z = (Math.random() - 0.5) * 80;
            enemyModel.position.set(x, 0.5, z);
            scene.add(enemyModel);

            const enemyShape = new CANNON.Sphere(0.5);
            const enemyBody = new CANNON.Body({ mass: 1 });
            enemyBody.addShape(enemyShape);
            enemyBody.position.set(x, 0.5, z);
            world.addBody(enemyBody);

            enemies.push({ model: enemyModel, body: enemyBody });
        }

        // Spawn secrets
        function spawnSecret() {
            const secretGeometry = new THREE.SphereGeometry(0.3, 32, 32);
            const secretMaterial = new THREE.MeshBasicMaterial({ color: 0xffff00 });
            const secretModel = new THREE.Mesh(secretGeometry, secretMaterial);
            const x = (Math.random() - 0.5) * 80;
            const z = (Math.random() - 0.5) * 80;
            secretModel.position.set(x, 0.3, z);
            scene.add(secretModel);

            const secretShape = new CANNON.Sphere(0.3);
            const secretBody = new CANNON.Body({ mass: 0 });
            secretBody.addShape(secretShape);
            secretBody.position.set(x, 0.3, z);
            world.addBody(secretBody);

            secrets.push({ model: secretModel, body: secretBody });
        }

        // Shoot bullets
        function shootBullet() {
            const bulletGeometry = new THREE.SphereGeometry(0.1, 32, 32);
            const bulletMaterial = new THREE.MeshBasicMaterial({ color: 0x00ffff });
            const bulletModel = new THREE.Mesh(bulletGeometry, bulletMaterial);
            bulletModel.position.copy(playerModel.position);
            scene.add(bulletModel);

            const bulletShape = new CANNON.Sphere(0.1);
            const bulletBody = new CANNON.Body({ mass: 0.1 });
            bulletBody.addShape(bulletShape);
            bulletBody.position.copy(playerBody.position);
            const direction = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion).normalize().multiplyScalar(20); // Shoot in camera direction
            bulletBody.velocity.set(direction.x, direction.y, direction.z);
            world.addBody(bulletBody);

            bullets.push({ model: bulletModel, body: bulletBody, life: 2 });
        }

        // Update game state
        function update(delta) {
            if (isPaused || gameOver) return;

            // Update physics
            world.step(delta);

            // Sync Three.js with Cannon.js
            playerModel.position.copy(playerBody.position);
            playerModel.quaternion.copy(playerBody.quaternion);

            // Player movement
            const velocity = difficulty === "Easy" ? 5 : difficulty === "Medium" ? 6 : difficulty === "Hard" ? 7 : 8;
            if (keys.w) playerBody.velocity.z = -velocity;
            if (keys.s) playerBody.velocity.z = velocity;
            if (keys.a) playerBody.velocity.x = -velocity;
            if (keys.d) playerBody.velocity.x = velocity;
            if (keys.space && playerBody.position.y <= 0.6) playerBody.velocity.y = 5;

            // Camera follows player
            const offset = new THREE.Vector3(0, 5, 10).applyQuaternion(camera.quaternion);
            camera.position.copy(playerBody.position).add(offset);
            camera.lookAt(playerBody.position);

            // Update enemies
            enemies.forEach((enemy, index) => {
                enemy.model.position.copy(enemy.body.position);
                enemy.model.quaternion.copy(enemy.body.quaternion);
                const direction = playerBody.position.clone().vsub(enemy.body.position).scale(0.01);
                enemy.body.velocity.x += direction.x;
                enemy.body.velocity.z += direction.z;

                // Check collision with player
                if (enemy.body.position.distanceTo(playerBody.position) < 1) {
                    health -= 10;
                    document.getElementById('health-text').textContent = `Health: ${health}`;
                    if (health <= 0) endGame();
                }
            });

            // Update secrets
            secrets.forEach((secret, index) => {
                secret.model.position.copy(secret.body.position);
                if (secret.body.position.distanceTo(playerBody.position) < 1) {
                    scene.remove(secret.model);
                    world.removeBody(secret.body);
                    secrets.splice(index, 1);
                    score += 50;
                    secretsFound++;
                    document.getElementById('secrets-text').textContent = `Secrets: ${secretsFound}`;
                    if (Math.random() < 0.3) activatePowerUp();
                }
            });

            // Update bullets
            bullets.forEach((bullet, bIndex) => {
                bullet.model.position.copy(bullet.body.position);
                bullet.life -= delta;
                if (bullet.life <= 0) {
                    scene.remove(bullet.model);
                    world.removeBody(bullet.body);
                    bullets.splice(bIndex, 1);
                } else {
                    for (let eIndex = enemies.length - 1; eIndex >= 0; eIndex--) {
                        const enemy = enemies[eIndex];
                        if (bullet.body.position.distanceTo(enemy.body.position) < 0.6) {
                            scene.remove(enemy.model);
                            world.removeBody(enemy.body);
                            enemies.splice(eIndex, 1);
                            scene.remove(bullet.model);
                            world.removeBody(bullet.body);
                            bullets.splice(bIndex, 1);
                            score += 100;
                            enemiesDefeated++;
                            document.getElementById('score-text').textContent = `Score: ${score}`;
                            break;
                        }
                    }
                }
            });

            // Update HUD
            timeLeft -= delta;
            document.getElementById('score-text').textContent = `Score: ${score}`;
            document.getElementById('timer-text').textContent = `Time: ${Math.max(0, Math.floor(timeLeft))}`;
            document.getElementById('health-text').textContent = `Health: ${health}`;
            document.getElementById('secrets-text').textContent = `Secrets: ${secretsFound}`;

            if (timeLeft <= 0) endGame();
        }

        // Animation loop
        function animate() {
            requestAnimationFrame(animate);
            const currentTime = performance.now();
            const delta = (currentTime - lastTime) / 1000;
            lastTime = currentTime;
            update(delta);
            renderer.render(scene, camera);
        }

        // Game controls
        function startGame() {
            playerName = document.getElementById('player-name').value || "Player";
            playerAge = document.getElementById('player-age').value || 18;
            englishLevel = document.getElementById('english-level').value;
            difficulty = document.getElementById('difficulty').value;
            document.getElementById('main-menu').style.display = 'none';

            // Spawn initial enemies and secrets
            for (let i = 0; i < 5; i++) {
                spawnEnemy();
                spawnSecret();
            }

            // Start game loop
            animate();
        }

        function togglePause() {
            isPaused = !isPaused;
            document.getElementById('pause-menu').style.display = isPaused ? 'block' : 'none';
        }

        function resumeGame() {
            isPaused = false;
            document.getElementById('pause-menu').style.display = 'none';
        }

        function restartGame() {
            location.reload();
        }

        function exitToMainMenu() {
            location.reload();
        }

        function endGame() {
            gameOver = true;
            document.getElementById('certificate').style.display = 'block';
            document.getElementById('cert-name').textContent = `Name: ${playerName}`;
            document.getElementById('cert-age').textContent = `Age: ${playerAge}`;
            document.getElementById('cert-level').textContent = `English Level: ${englishLevel}`;
            document.getElementById('cert-difficulty').textContent = `Difficulty: ${difficulty}`;
            document.getElementById('cert-score').textContent = `Score: ${score}`;
            document.getElementById('cert-time').textContent = `Time Survived: ${Math.floor(60 - timeLeft)}s`;
            document.getElementById('cert-secrets').textContent = `Secrets Found: ${secretsFound}`;
            document.getElementById('cert-enemies').textContent = `Enemies Defeated: ${enemiesDefeated}`;
        }

        function activatePowerUp() {
            powerUpActive = true;
            powerUpNotification = document.getElementById('power-up-notification');
            powerUpNotification.textContent = "Speed Boost Activated!";
            powerUpNotification.style.display = 'block';
            setTimeout(() => {
                powerUpNotification.style.display = 'none';
                powerUpActive = false;
            }, 5000);
        }
    </script>
</body>
</html>