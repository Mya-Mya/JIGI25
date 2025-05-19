from .vehicle import Vehicle
from .vehiclecamera import VehicleCamera
from carla import Client, World, WorldSettings, BlueprintLibrary, VehicleControl
from copy import deepcopy


def init_client(
        host="127.0.0.1",
        port=2000
) -> Client:
    client = Client(host, port)
    client.set_timeout(100.0)
    return client


def get_ready(
        host="127.0.0.1",
        port=2000
) -> tuple[Client, World, WorldSettings, BlueprintLibrary]:
    client = init_client(host, port)
    world: World = client.get_world()
    world_settings: WorldSettings = world.get_settings()
    bpl: BlueprintLibrary = world.get_blueprint_library()
    return client, world, world_settings, bpl


def copy_vehicle_control(control: VehicleControl) -> VehicleControl:
    x = VehicleControl()
    x.steer = deepcopy(control.steer)
    x.throttle = deepcopy(control.throttle)
    x.brake = deepcopy(control.brake)
    x.gear = deepcopy(control.gear)
    x.hand_brake = deepcopy(control.hand_brake)
    x.reverse = deepcopy(control.reverse)
    return x
