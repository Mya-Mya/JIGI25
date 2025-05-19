# 標準
from time import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from copy import deepcopy

# サードパーティー
from carla import *
import pygame
from pygame.surface import Surface
from pandas import DataFrame
from numpy import ndarray, zeros, arctan2
from numpy import array as npa

# 自プロジェクト
import carlautils
from pygamecomponents import *
from vehiclemodel import *
from vehiclecontrollers import *
from mppi import *
from keepoutareas import *

# PyGame初期化
pygame.init()
screen = pygame.display.set_mode((1600, 900), pygame.HWSURFACE | pygame.DOUBLEBUF)
clock = pygame.time.Clock()

# テレメトリ
session_id = datetime.now().strftime("%Y%m%d.%H%M%S")
game_step = -1


@dataclass
class TelemetryRecord:
    # 車
    VehicleLocationX: float = 0.
    VehicleLocationY: float = 0.
    VehicleVelocityX: float = 0.
    VehicleVelocityY: float = 0.
    VehicleSpeed: float = 0.
    VehicleAccelerationX: float = 0.
    VehicleAccelerationY: float = 0.
    VehicleDirection: float = 0.
    # 障害物
    ObstacleLocationX: float = 0.,
    ObstacleLocationY: float = 0.,
    ObstacleRadius2: float = 0.,
    # 制御
    ControlThrottle: float = 0.
    ControlNominalSteer: float = 0.
    ControlFilteredSteer: float = 0.
    ControlBrake: float = 0.
    # MPPI
    MPPIFilterComputationTime: float = 0.
    MPPIFilterFilteringFlowName: str = ""
    MPPIOptimalSteerTrajectory: list = field(default_factory=list)
    # ゲームシステム
    GameTimestamp: float = 0.
    GameActualFreshrate: float = 0.
    GameStep: int = 0


telemetry_history: list[TelemetryRecord] = []
is_telemetry_recording = False
# テレメトリの内容を一部表示するGUIコンポーネント
telemetry_view = DictViewer(width=250, key_width=130, keys=["X", "Y", "Speed", "Brake", "MPPI Time"])

# CARLAとの通信樹立
client, world, world_settings, bpl = carlautils.get_ready()

# CARLA内の物体の管理
vehicle = carlautils.Vehicle(client=client, bpid="vehicle.nissan.patrol")
vehicle_camera_view = Surface((1600, 900))
vehicle_camera = carlautils.VehicleCamera(
    client=client, vehicle=vehicle, width=vehicle_camera_view.get_width(), height=vehicle_camera_view.get_height()
)

# G29：G29筐体をお持ちでない方はコメントアウト
import LogitechSteeringWheelPy as lsw

lsw.load_dll("Dependencies/LogitechSteeringWheelEnginesWrapper.dll", reload=True)
lsw.initialize_with_window(True, pygame.display.get_wm_info()["window"])
# CARLAの世界ではy軸が数学とは逆なので，右回りの方向に正の角度を与えれば辻褄が全て合う．
g29 = lsw.G29(index=0, positive_angle="clockwise")
# ノミナル入力を出力する制御器
nominal_controller = G29Controller(g29=g29)

# G29筐体をお持ちでない方は，何かしらの方法でノミナル制御器が必要
# 以下は固定された制御入力を出力し続けるノミナル制御器
# nominal_control = VehicleControl()
# nominal_control.throttle = 0.3
# nominal_control.steer = 0.0
# nominal_controller = ConstantVehicleController(vehicle_control=nominal_control)

# MPPI介入制御器
mppi_filter = MPPIFilter(
    vehiclemodel=VehicleModel(),
    samplesize=512,
    horizon=50,
    command_std=0.7,
    temperature=1.0,
    violation_weight_decay=0.90
)

# ステアリング入力についてのGUI
command_view = IntervenableScalarView(width=200, min_value=-1.0, max_value=1.0)

# 障害物：障害物は好きな場所に配置できる
obstacle_actor: Optional[Actor] = None


def spawn_obstacle():
    global obstacle_actor, obstacle_x, obstacle_y
    if obstacle_actor:
        obstacle_actor.destroy()
    # 障害物の位置決め
    transform: Transform = vehicle.actor.get_transform()
    forward: Vector3D = transform.get_forward_vector()  # 車の向き
    forward_x_std = forward.x
    forward_y_std = forward.y
    scale = 30 / (forward_x_std ** 2 + forward_y_std ** 2) ** 0.5
    forward_x = forward_x_std * scale
    forward_y = forward_y_std * scale  # 自分より30 m前
    transform.location.x += forward_x
    transform.location.y += forward_y
    transform.location.z += 1.0  # ちょっと浮かせる（自分と全く同じ高さだと稀に地面を突き破って落下する）
    # 世界に置く
    try:
        obstacle_actor = world.try_spawn_actor(bpl.find("static.prop.atm"), transform)
        obstacle_actor.set_simulate_physics(True)
    except:
        print("Error Spawning Obstacle")
    # MPPI介入制御器に反映する
    mppi_filter.set_keepoutareas([
        CircleKeepoutArea(
            transform.location.x,
            transform.location.y,
            4
        )
    ])


gaming = True
while gaming:
    clock.tick_busy_loop(25)  # 25 Hzで動作させる

    # テレメトリ
    game_step += 1
    T = TelemetryRecord()
    ## ゲーム環境に関して
    T.GameTimestamp = time()
    T.GameActualFreshrate = clock.get_fps()
    T.GameStep = game_step
    ## 車について
    location: Location = vehicle.actor.get_location()
    velocity: Vector3D = vehicle.actor.get_velocity()
    acceleration: Vector3D = vehicle.actor.get_acceleration()
    T.VehicleLocationX = location.x
    T.VehicleLocationY = location.y
    T.VehicleVelocityX = velocity.x
    T.VehicleVelocityY = velocity.y
    T.VehicleSpeed = ((velocity.x * velocity.x) + (velocity.y * velocity.y)) ** 0.5
    T.VehicleAccelerationX = acceleration.x
    T.VehicleAccelerationY = acceleration.y
    T.VehicleDirection = arctan2(velocity.y, velocity.x)
    ## 障害物について
    if mppi_filter.keepoutareas:
        # 当ゲームに限り，障害物は1つだけで，それは`CircleKeepoutArea`である．
        koa: CircleKeepoutArea = mppi_filter.keepoutareas[0]
        T.ObstacleLocationX = koa.x
        T.ObstacleLocationY = koa.y
        T.ObstacleRadius2 = koa.radius_2

    # G29筐体からの信号を読み取る：G29筐体をお持ちでない方はコメントアウト
    lsw.update()
    g29.update()

    # 制御入力を作る
    nominal_controller.tick()
    nominal_control = nominal_controller.get_vehicle_control()
    nominal_steer = nominal_control.steer
    start = time()
    mppi_result = mppi_filter.get_filtered_command(
        initial_location_x=T.VehicleLocationX,
        initial_location_y=T.VehicleLocationY,
        initial_direction=T.VehicleDirection,
        initial_speed=T.VehicleSpeed,
        nominal_command=nominal_steer,
    )
    end = time()
    filtered_steer = mppi_result.filtered_command
    filtered_control = carlautils.copy_vehicle_control(nominal_control)
    filtered_control.steer = filtered_steer
    ## テレメトリへの書き込み
    T.ControlThrottle = nominal_control.throttle  # アクセル
    T.ControlBrake = nominal_control.brake
    T.ControlNominalSteer = nominal_steer
    T.ControlFilteredSteer = filtered_steer
    T.MPPIFilterComputationTime = end - start  # MPPI介入制御の動作時間（多分すごい早いはず）
    T.MPPIFilterFilteringFlowName = mppi_result.flow.name
    if mppi_result.commands_list is not None:
        T.MPPIOptimalSteerTrajectory = \
            sum(mppi_result.commands_list.T * mppi_result.sample_weights, axis=1).tolist()
    ## GUIへの反映
    if mppi_result.flow == FilteringFlow.Intervention:
        command_view.set_intervening(
            nominal_value=nominal_steer,
            intervening_value=filtered_steer
        )
    else:
        command_view.set_nominal(nominal_steer)
    ## 車へ入力
    vehicle.apply_vehicle_control(filtered_control)

    # G29の三角ボタンを押したら障害物が現れる
    if g29.is_released(g29.Button.Triangle):
        spawn_obstacle()

    # GUI
    telemetry_view.set_values([
        f"{T.VehicleLocationX:.04f}",
        f"{T.VehicleLocationY:.04f}",
        f"{T.VehicleSpeed:.04f}",
        f"{T.ControlBrake:.04f}",
        f"{T.MPPIFilterComputationTime:.04f}"
    ])
    # 画面描画
    screen.fill((0, 0, 0))
    if vehicle_camera.image_array is not None:
        surface = pygame.surfarray.make_surface(vehicle_camera.image_array.swapaxes(0, 1))
        vehicle_camera_view.blit(surface, (0, 0))
    screen.blit(vehicle_camera_view, (0, 0))
    screen.blit(command_view.surface, (1300, 500))
    screen.blit(telemetry_view.surface, (200, 500))
    pygame.display.flip()

    # G29の丸ボタンを押したらテレメトリを記録・保存するようにする
    if g29.is_triggered(g29.Button.Circle):
        is_telemetry_recording = not is_telemetry_recording
        print("Recording Telemetry:", is_telemetry_recording)

    # テレメトリを記録する
    if is_telemetry_recording:
        telemetry_history.append(T)

    for event in pygame.event.get():
        if event.type == pygame.KEYUP:
            # スペースキーを押したら車カメラを保存する
            if event.key == pygame.K_SPACE:
                vehicle_camera.take_screenshot_async(save_to=Path(f"Records/{session_id}.{game_step}.pkl"))
        if event.type == pygame.QUIT:# 終了確認
            gaming = False

# CARLAの世界から物を消す
vehicle.destroy()
vehicle_camera.destroy()
if obstacle_actor is not None:
    obstacle_actor.destroy()
# G29筐体との通信を遮断する
lsw.shutdown()
# PyGameを終了する
pygame.quit()

# テレメトリを保存する
if telemetry_history:
    df = DataFrame(telemetry_history)
    df.to_csv(Path(f"Records/{session_id}.csv"))

exit(0)