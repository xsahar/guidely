use std::collections::HashMap;
use std::env;
use std::net::{SocketAddr, UdpSocket};
use std::time::{Duration, Instant};

use guidely::shared::collision::move_with_collision;
use guidely::shared::player::Player;
use guidely::shared::protocol::{ClientMessage, PlayerState, ServerMessage};
use guidely::shared::world::level_by_index;

pub struct Server {
    socket: UdpSocket,
    players: HashMap<SocketAddr, Player>,
    inputs: HashMap<SocketAddr, (f32, f32)>,
    last_seen: HashMap<SocketAddr, Instant>,
    level: u8,
    tick: u64,
    next_id: u32,
}

impl Server {
    pub fn new() -> std::io::Result<Self> {
        Self::new_with_addr("0.0.0.0:8080")
    }

    pub fn new_with_addr(addr: &str) -> std::io::Result<Self> {
        let socket = UdpSocket::bind(addr)?;
        socket.set_nonblocking(true)?;
        Ok(Self {
            socket,
            players: HashMap::new(),
            inputs: HashMap::new(),
            last_seen: HashMap::new(),
            level: 1,
            tick: 0,
            next_id: 1,
        })
    }

    fn send_to(&self, addr: SocketAddr, message: &ServerMessage) -> std::io::Result<()> {
        let payload = bincode::serialize(message)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        self.socket.send_to(&payload, addr)?;
        Ok(())
    }

    fn snapshot(&self) -> ServerMessage {
        let players = self
            .players
            .values()
            .map(|p| PlayerState {
                id: p.id,
                username: p.username.clone(),
                level: p.level,
                x: p.x,
                y: p.y,
                angle: p.angle,
            })
            .collect();

        ServerMessage::Snapshot {
            tick: self.tick,
            players,
        }
    }

    pub fn run(&mut self) {
        let mut buffer = [0u8; 2048];
        let mut last_broadcast = Instant::now();

        loop {
            loop {
                match self.socket.recv_from(&mut buffer) {
                    Ok((len, addr)) => {
                        if let Ok(message) = bincode::deserialize::<ClientMessage>(&buffer[..len]) {
                            match message {
                                ClientMessage::Hello {
                                    username,
                                    protocol_version: _,
                                } => {
                                    let world = level_by_index(self.level);
                                    let spawn =
                                        world.spawn_points.first().copied().unwrap_or((1.5, 1.5));
                                    let player = Player::new(
                                        self.next_id,
                                        &username,
                                        spawn.0,
                                        spawn.1,
                                        self.level,
                                    );
                                    self.next_id += 1;
                                    self.players.insert(addr, player.clone());
                                    self.inputs.insert(addr, (0.0, 0.0));
                                    self.last_seen.insert(addr, Instant::now());
                                    let _ = self.send_to(
                                        addr,
                                        &ServerMessage::Welcome {
                                            player_id: player.id,
                                            level: self.level,
                                        },
                                    );
                                    println!("Connected {} as player {}", username, player.id);
                                }
                                ClientMessage::Input {
                                    sequence: _,
                                    turn,
                                    move_forward,
                                } => {
                                    self.inputs.insert(addr, (turn, move_forward));
                                    self.last_seen.insert(addr, Instant::now());
                                }
                                ClientMessage::ChangeLevel { level } => {
                                    self.level = level.clamp(1, 3);
                                    let world = level_by_index(self.level);
                                    if let Some(spawn) = world.spawn_points.first().copied() {
                                        for player in self.players.values_mut() {
                                            player.level = self.level;
                                            player.x = spawn.0;
                                            player.y = spawn.1;
                                        }
                                    }
                                    self.last_seen.insert(addr, Instant::now());
                                }
                                ClientMessage::Disconnect => {
                                    self.players.remove(&addr);
                                    self.inputs.remove(&addr);
                                    self.last_seen.remove(&addr);
                                    println!("Disconnected client {}", addr);
                                }
                            }
                        }
                    }
                    Err(ref err) if err.kind() == std::io::ErrorKind::WouldBlock => break,
                    Err(_) => break,
                }
            }

            self.tick += 1;
            if last_broadcast.elapsed() >= Duration::from_millis(50) {
                let now = Instant::now();
                let stale_clients: Vec<SocketAddr> = self
                    .last_seen
                    .iter()
                    .filter_map(|(addr, seen)| {
                        (now.duration_since(*seen) > Duration::from_secs(3)).then_some(*addr)
                    })
                    .collect();
                for addr in stale_clients {
                    self.players.remove(&addr);
                    self.inputs.remove(&addr);
                    self.last_seen.remove(&addr);
                }

                for (addr, player) in self.players.iter_mut() {
                    let (turn, move_forward) = self.inputs.get(addr).copied().unwrap_or((0.0, 0.0));
                    let turn = turn.clamp(-1.0, 1.0);
                    player.angle += turn * 0.06;
                    let speed = move_forward * 0.10;
                    let dx = speed * player.angle.cos();
                    let dy = speed * player.angle.sin();
                    let level = level_by_index(player.level);
                    let next = move_with_collision(
                        (player.x, player.y),
                        (player.x + dx, player.y + dy),
                        &level.tiles,
                        0.35,
                    );
                    player.x = next.0;
                    player.y = next.1;
                }

                let snapshot = self.snapshot();
                let payload = bincode::serialize(&snapshot).unwrap();
                for addr in self.players.keys().copied().collect::<Vec<_>>() {
                    let _ = self.socket.send_to(&payload, addr);
                }
                last_broadcast = Instant::now();
            }
        }
    }
}

fn main() {
    let bind_addr = env::args()
        .nth(1)
        .unwrap_or_else(|| "0.0.0.0:8080".to_string());
    let mut server = Server::new_with_addr(&bind_addr).expect("Failed to start server");
    println!("Server listening on {}", bind_addr);
    server.run();
}
