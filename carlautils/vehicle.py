import random

import carla
from typing import List, Literal, Optional

VehicleBPID = Literal[
    'vehicle.sprinter.mercedes',
    'vehicle.ambulance.ford',
    'vehicle.firetruck.actors',
    'vehicle.lincoln.mkz',
    'vehicle.dodgecop.charger',
    'vehicle.mini.cooper',
    'vehicle.dodge.charger',
    'vehicle.fuso.mitsubishi',
    'vehicle.nissan.patrol',
    'vehicle.carlacola.actors',
    'vehicle.taxi.ford'
]


class Vehicle:
    @staticmethod
    def get_vehicle_bpid_list(client: carla.Client) -> List[str]:
        world: carla.World = client.get_world()
        bpl: carla.BlueprintLibrary = world.get_blueprint_library()
        bpid_list = []
        for bp in bpl.filter("vehicle.*"):
            bp: carla.ActorBlueprint
            bpid_list.append(bp.id)
        return bpid_list

    def __init__(
            self,
            client: carla.Client,
            bpid: VehicleBPID,
            spawn_point: Optional[carla.Transform] = None
    ):
        world: carla.World = client.get_world()
        bpl: carla.BlueprintLibrary = world.get_blueprint_library()

        # ブループリントを設定
        bp: carla.ActorBlueprint = bpl.find(bpid)
        if bp.has_attribute("is_invincible"):
            bp.set_attribute("is_invincible", "true")

        self.max_speed = 1.589
        self.max_speed_fast = 3.713
        if bp.has_attribute("speed"):
            speed = bp.get_attribute("speed")
            self.max_speed = speed.recommended_values[1]
            self.max_speed_fast = speed.reccommended_values[2]

        try:
            self.map: carla.Map = world.get_map()
        except RuntimeError as e:
            print(e)
            print("このサーバにはOpenDRIVEファイルがありません．")
            exit(1)

        # 設置位置を決める
        if spawn_point is None:
            spawn_points = self.map.get_spawn_points()
            spawn_point = random.choice(spawn_points) if spawn_points else carla.Transform()

        # 車を世界に落とす
        self.actor: carla.Vehicle = world.try_spawn_actor(bp, spawn_point)
        assert isinstance(self.actor, carla.Vehicle)

        # 物理モデルの改善
        physics_control: carla.VehiclePhysicsControl = self.actor.get_physics_control()
        physics_control.use_sweep_wheel_collision = True
        self.actor.apply_physics_control(physics_control)

        # ライトに関する変数
        self.lights = carla.VehicleLightState.NONE

    def apply_vehicle_control(self, control: carla.VehicleControl):
        # 物理入力
        self.actor.apply_control(control)

        # ライトを更新
        next_lights = self.lights
        if control.brake > 0.0:
            next_lights |= carla.VehicleLightState.Brake
        else:
            next_lights &= ~carla.VehicleLightState.Brake
        if control.reverse:
            next_lights |= carla.VehicleLightState.Reverse
        else:
            next_lights &= ~carla.VehicleLightState.Reverse
        if next_lights != self.lights:
            self.lights = next_lights
            self.actor.set_light_state(carla.VehicleLightState(next_lights))

    def destroy(self):
        self.actor.destroy()
