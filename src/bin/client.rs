use std::net::UdpSocket;
use std::time::{Duration, Instant};

use macroquad::prelude::*;

use guidely::shared::protocol::{ClientMessage, ServerMessage};
use guidely::shared::world::level_by_index;

struct ConnectionForm {
    server_ip: String,
    username: String,
    level: u8,
    editing_server_ip: bool,
    error: String,
}

impl Default for ConnectionForm {
    fn default() -> Self {
        Self {
            server_ip: "127.0.0.1:8080".to_string(),
            username: String::new(),
            level: 1,
            editing_server_ip: true,
            error: String::new(),
        }
    }
}

impl ConnectionForm {
    fn update(&mut self) -> Option<(String, String, u8)> {
        if is_key_pressed(KeyCode::Key1) {
            self.level = 1;
        }
        if is_key_pressed(KeyCode::Key2) {
            self.level = 2;
        }
        if is_key_pressed(KeyCode::Key3) {
            self.level = 3;
        }
        if is_key_pressed(KeyCode::Tab) {
            self.editing_server_ip = !self.editing_server_ip;
        }
        if is_key_pressed(KeyCode::Backspace) {
            let field = if self.editing_server_ip {
                &mut self.server_ip
            } else {
                &mut self.username
            };
            field.pop();
        }
        while let Some(character) = get_char_pressed() {
            if !character.is_control() {
                let field = if self.editing_server_ip {
                    &mut self.server_ip
                } else {
                    &mut self.username
                };
                if field.len() < 64 {
                    field.push(character);
                }
            }
        }

        if is_key_pressed(KeyCode::Enter) {
            if self.server_ip.trim().is_empty() || self.username.trim().is_empty() {
                self.error = "Enter both a server address and username".to_string();
            } else {
                return Some((
                    self.server_ip.trim().to_string(),
                    self.username.trim().to_string(),
                    self.level,
                ));
            }
        }
        None
    }
}

fn draw_connection_form(form: &ConnectionForm) {
    clear_background(Color::new(0.08, 0.12, 0.15, 1.0));
    let center_x = screen_width() * 0.5 - 220.0;
    draw_text("GUIDELY", center_x, 150.0, 44.0, WHITE);
    draw_text(
        "Connect to a Maze Wars server",
        center_x,
        184.0,
        20.0,
        LIGHTGRAY,
    );

    draw_text("SERVER IP:PORT", center_x, 245.0, 18.0, WHITE);
    draw_rectangle_lines(
        center_x,
        260.0,
        440.0,
        48.0,
        2.0,
        if form.editing_server_ip { GREEN } else { GRAY },
    );
    draw_text(&form.server_ip, center_x + 14.0, 292.0, 22.0, WHITE);

    draw_text("USERNAME", center_x, 350.0, 18.0, WHITE);
    draw_rectangle_lines(
        center_x,
        365.0,
        440.0,
        48.0,
        2.0,
        if !form.editing_server_ip { GREEN } else { GRAY },
    );
    draw_text(&form.username, center_x + 14.0, 397.0, 22.0, WHITE);

    draw_text(
        "TAB: switch field    ENTER: connect",
        center_x,
        465.0,
        18.0,
        LIGHTGRAY,
    );
    draw_text(
        &format!("LEVEL: {}    Press 1, 2, or 3 to choose", form.level),
        center_x,
        500.0,
        18.0,
        LIGHTGRAY,
    );
    if !form.error.is_empty() {
        draw_text(&form.error, center_x, 535.0, 18.0, RED);
    }
}

struct ClientRuntime {
    socket: UdpSocket,
    username: String,
    state: Option<ServerMessage>,
    player_id: Option<u32>,
    sequence: u64,
    move_value: f32,
    turn_value: f32,
    last_fps: f64,
    last_input: Instant,
}

impl ClientRuntime {
    fn new(server_ip: &str, username: &str) -> std::io::Result<Self> {
        let socket = UdpSocket::bind("0.0.0.0:0")?;
        socket.set_nonblocking(true)?;
        socket.connect(server_ip)?;
        Ok(Self {
            socket,
            username: username.to_string(),
            state: None,
            player_id: None,
            sequence: 0,
            move_value: 0.0,
            turn_value: 0.0,
            last_fps: 0.0,
            last_input: Instant::now(),
        })
    }

    fn hello(&self) -> std::io::Result<()> {
        let msg = ClientMessage::Hello {
            username: self.username.clone(),
            protocol_version: 1,
        };
        let payload = bincode::serialize(&msg).unwrap();
        self.socket.send(&payload)?;
        Ok(())
    }

    fn change_level(&self, level: u8) {
        let message = ClientMessage::ChangeLevel { level };
        let _ = self.socket.send(&bincode::serialize(&message).unwrap());
    }

    fn poll_server(&mut self) {
        let mut buffer = [0u8; 4096];
        loop {
            match self.socket.recv(&mut buffer) {
                Ok(len) => {
                    if let Ok(message) = bincode::deserialize::<ServerMessage>(&buffer[..len]) {
                        match &message {
                            ServerMessage::Welcome { player_id, .. } => {
                                self.player_id = Some(*player_id);
                            }
                            ServerMessage::Snapshot { .. } => {
                                self.state = Some(message);
                            }
                            ServerMessage::Error(_) => {}
                        }
                    }
                }
                Err(ref err) if err.kind() == std::io::ErrorKind::WouldBlock => break,
                Err(_) => break,
            }
        }
    }

    fn send_input(&mut self) {
        if self.player_id.is_none() || self.last_input.elapsed() < Duration::from_millis(50) {
            return;
        }

        self.last_input = Instant::now();
        self.sequence += 1;
        let msg = ClientMessage::Input {
            sequence: self.sequence,
            turn: self.turn_value,
            move_forward: self.move_value,
        };
        let payload = bincode::serialize(&msg).unwrap();
        let _ = self.socket.send(&payload);
    }

    fn update_input(&mut self) {
        let mut move_value = 0.0;
        let mut turn_value = 0.0;

        let forward_pressed = is_key_down(KeyCode::W) || is_key_down(KeyCode::Up);
        let backward_pressed = is_key_down(KeyCode::S) || is_key_down(KeyCode::Down);
        let left_pressed = is_key_down(KeyCode::A) || is_key_down(KeyCode::Left);
        let right_pressed = is_key_down(KeyCode::D) || is_key_down(KeyCode::Right);

        if forward_pressed && !backward_pressed {
            move_value = 1.0;
        }
        if backward_pressed && !forward_pressed {
            move_value = -1.0;
        }
        if left_pressed && !right_pressed {
            turn_value = -1.0;
        }
        if right_pressed && !left_pressed {
            turn_value = 1.0;
        }

        self.move_value = move_value;
        self.turn_value = turn_value;

        if is_key_pressed(KeyCode::Q) {
            let msg = ClientMessage::Disconnect;
            let _ = self.socket.send(&bincode::serialize(&msg).unwrap());
            std::process::exit(0);
        }
    }
}

fn draw_maze_and_players(runtime: &ClientRuntime) {
    let sky_color = Color::new(0.18, 0.24, 0.29, 1.0);
    let floor_color = Color::new(0.16, 0.15, 0.13, 1.0);
    clear_background(sky_color);
    draw_rectangle(
        0.0,
        screen_height() * 0.48,
        screen_width(),
        screen_height() * 0.52,
        floor_color,
    );

    let map = vec![
        vec![1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        vec![1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        vec![1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1],
        vec![1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1],
        vec![1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1],
        vec![1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
        vec![1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1],
        vec![1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1],
        vec![1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1],
        vec![1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
        vec![1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1],
        vec![1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1],
        vec![1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1],
        vec![1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        vec![1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1],
        vec![1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    ];
    let current_level = runtime
        .player_id
        .and_then(|player_id| {
            runtime.state.as_ref().and_then(|state| match state {
                ServerMessage::Snapshot { players, .. } => players
                    .iter()
                    .find(|player| player.id == player_id)
                    .map(|player| player.level),
                _ => None,
            })
        })
        .unwrap_or(1);
    let map = map_for_level(current_level, &map);

    let cell = 10.0;
    let offset_x = 16.0;
    let offset_y = 104.0;
    let player_x = runtime
        .player_id
        .and_then(|_| runtime.state.as_ref())
        .and_then(|state| match state {
            ServerMessage::Snapshot { players, .. } => players
                .iter()
                .find(|p| Some(p.id) == runtime.player_id)
                .map(|p| p.x),
            _ => None,
        })
        .unwrap_or(1.5);
    let player_y = runtime
        .player_id
        .and_then(|_| runtime.state.as_ref())
        .and_then(|state| match state {
            ServerMessage::Snapshot { players, .. } => players
                .iter()
                .find(|p| Some(p.id) == runtime.player_id)
                .map(|p| p.y),
            _ => None,
        })
        .unwrap_or(1.5);
    let player_angle = runtime
        .player_id
        .and_then(|_| runtime.state.as_ref())
        .and_then(|state| match state {
            ServerMessage::Snapshot { players, .. } => players
                .iter()
                .find(|p| Some(p.id) == runtime.player_id)
                .map(|p| p.angle),
            _ => None,
        })
        .unwrap_or(0.0);

    draw_first_person(&map, player_x, player_y, player_angle);
    for (y, row) in map.iter().enumerate() {
        for (x, cell_value) in row.iter().enumerate() {
            let px = offset_x + x as f32 * cell;
            let py = offset_y + y as f32 * cell;
            if *cell_value == 1 {
                draw_rectangle(px, py, cell, cell, DARKGRAY);
            } else {
                draw_rectangle(px, py, cell, cell, LIGHTGRAY);
            }
        }
    }

    let player_px = offset_x + player_x * cell;
    let player_py = offset_y + player_y * cell;
    draw_circle(player_px, player_py, 4.0, GREEN);

    if let Some(ServerMessage::Snapshot { players, .. }) = &runtime.state {
        for p in players {
            if Some(p.id) == runtime.player_id || p.level != current_level {
                continue;
            }
            let px = offset_x + (p.x as f32) * cell;
            let py = offset_y + (p.y as f32) * cell;
            draw_circle(px, py, 4.0, RED);
        }
    }

    draw_text("GUIDELY", 20.0, 28.0, 30.0, WHITE);
    draw_text(
        &format!("Player: {}", runtime.username),
        20.0,
        55.0,
        18.0,
        WHITE,
    );
    draw_text(
        &format!("FPS: {:.1}", runtime.last_fps),
        20.0,
        78.0,
        18.0,
        WHITE,
    );
    draw_text("MINIMAP", offset_x, offset_y - 12.0, 16.0, WHITE);
    draw_text(
        &format!("LEVEL {}", current_level),
        offset_x + 72.0,
        offset_y - 12.0,
        16.0,
        WHITE,
    );
    draw_text(
        "WASD move, Q quit",
        20.0,
        screen_height() - 20.0,
        18.0,
        WHITE,
    );
}

fn draw_first_person(map: &[Vec<i32>], player_x: f32, player_y: f32, player_angle: f32) {
    let view_x = 0.0;
    let view_y = 40.0;
    let view_width = screen_width().max(160.0);
    let view_height = (screen_height() - 88.0).max(180.0);
    let horizon = view_y + view_height * 0.48;

    draw_rectangle(
        view_x,
        view_y,
        view_width,
        view_height * 0.48,
        Color::new(0.18, 0.24, 0.29, 1.0),
    );
    draw_rectangle(
        view_x,
        horizon,
        view_width,
        view_height * 0.52,
        Color::new(0.16, 0.15, 0.13, 1.0),
    );

    let field_of_view = std::f32::consts::FRAC_PI_2;
    let columns = view_width as i32;
    for column in 0..columns {
        let screen_position = column as f32 / columns as f32;
        let ray_angle = player_angle + (screen_position - 0.5) * field_of_view;
        let direction_x = ray_angle.cos();
        let direction_y = ray_angle.sin();
        let mut distance = 0.05;
        let mut wall_distance = 20.0;

        while distance < 20.0 {
            let ray_x = player_x + direction_x * distance;
            let ray_y = player_y + direction_y * distance;
            let map_x = ray_x.floor() as i32;
            let map_y = ray_y.floor() as i32;
            if map_y < 0 || map_y >= map.len() as i32 || map_x < 0 || map_x >= map[0].len() as i32 {
                wall_distance = distance;
                break;
            }
            if map[map_y as usize][map_x as usize] == 1 {
                wall_distance = distance;
                break;
            }
            distance += 0.03;
        }

        let corrected_distance = (wall_distance * (ray_angle - player_angle).cos()).max(0.1);
        let wall_height = (view_height / corrected_distance).min(view_height * 1.4);
        let wall_top = horizon - wall_height * 0.5;
        let brightness = (0.85 - corrected_distance * 0.035).clamp(0.18, 0.85);
        draw_rectangle(
            view_x + column as f32,
            wall_top,
            1.5,
            wall_height,
            Color::new(brightness * 0.42, brightness * 0.48, brightness * 0.52, 1.0),
        );
    }

    draw_line(
        view_x + view_width * 0.5 - 7.0,
        horizon,
        view_x + view_width * 0.5 + 7.0,
        horizon,
        1.0,
        WHITE,
    );
    draw_line(
        view_x + view_width * 0.5,
        horizon - 7.0,
        view_x + view_width * 0.5,
        horizon + 7.0,
        1.0,
        WHITE,
    );
    draw_text("FIELD VIEW", view_x + 12.0, view_y + 24.0, 18.0, WHITE);
}

fn map_for_level(level: u8, default_map: &[Vec<i32>]) -> Vec<Vec<i32>> {
    if level == 1 {
        return default_map.to_vec();
    }

    level_by_index(level)
        .tiles
        .into_iter()
        .map(|row| row.into_iter().map(i32::from).collect())
        .collect()
}

#[macroquad::main("Guidely")]
async fn main() {
    let mut form = ConnectionForm::default();
    let mut runtime: Option<ClientRuntime> = None;
    let mut last_frame = Instant::now();

    loop {
        if runtime.is_none() {
            if let Some((server_ip, username, level)) = form.update() {
                match ClientRuntime::new(&server_ip, &username) {
                    Ok(client) => {
                        if client.hello().is_ok() {
                            client.change_level(level);
                            runtime = Some(client);
                            form.error.clear();
                        } else {
                            form.error = "Could not send connection request".to_string();
                        }
                    }
                    Err(error) => {
                        form.error = format!("Connection failed: {}", error);
                    }
                }
            }
            draw_connection_form(&form);
            next_frame().await;
            continue;
        }

        let runtime = runtime.as_mut().expect("runtime created above");
        runtime.poll_server();
        runtime.update_input();
        if runtime.player_id.is_some() {
            runtime.send_input();
        }

        let dt = last_frame.elapsed().as_secs_f32();
        last_frame = Instant::now();
        runtime.last_fps = if dt > 0.0 { 1.0 / dt as f64 } else { 0.0 };

        draw_maze_and_players(&runtime);
        next_frame().await;
    }
}
