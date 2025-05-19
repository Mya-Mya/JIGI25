import carla
from carla import Transform, Location, Rotation, AttachmentType
import weakref
from typing import Optional
from numpy import frombuffer, reshape, dtype, ndarray
from .vehicle import Vehicle
from pathlib import Path
import threading, pickle

uint8 = dtype("uint8")


class VehicleCamera:
    def __init__(self, client: carla.Client, vehicle: Vehicle, width: int, height: int):
        world: carla.World = client.get_world()
        bpl: carla.BlueprintLibrary = world.get_blueprint_library()

        bp: carla.ActorBlueprint = bpl.find("sensor.camera.rgb")
        bp.set_attribute("image_size_x", str(width))
        bp.set_attribute("image_size_y", str(height))

        bound_x = 0.5 + vehicle.actor.bounding_box.extent.x
        bound_y = 0.5 + vehicle.actor.bounding_box.extent.y
        bound_z = 0.5 + vehicle.actor.bounding_box.extent.z

        transform = Transform(
            Location(x=-1.5 * bound_x, z=2.0 * bound_z),
            Rotation(pitch=20.0, )
        )
        self.actor: carla.Sensor = world.spawn_actor(
            bp,
            transform,
            attach_to=vehicle.actor,
            attachment_type=AttachmentType.SpringArmGhost
        )
        weak_self = weakref.ref(self)
        self.image_array: Optional[ndarray] = None
        self.actor.listen(lambda image: VehicleCamera.on_image_taken(weak_self, image))

    @staticmethod
    def on_image_taken(weak_self, image: carla.Image):
        self: VehicleCamera = weak_self()

        image.convert(carla.ColorConverter.Raw)
        x = frombuffer(image.raw_data, dtype=uint8)
        x = reshape(x, (image.height, image.width, 4))
        x = x[:, :, :3]
        x = x[:, :, ::-1]

        self.image_array = x

    def take_screenshot_sync(self, save_to: Path):
        save_to.write_bytes(pickle.dumps(self.image_array))
        print("Saved Screenshot to", save_to.name)

    def take_screenshot_async(self, save_to: Path):
        threading.Thread(target=self.take_screenshot_sync, args=(save_to,)).start()

    def destroy(self):
        self.actor.stop()
        self.actor.destroy()
