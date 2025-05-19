import carla
from abc import ABC, abstractmethod
import LogitechSteeringWheelPy as lsw
from LogitechSteeringWheelPy.g29 import  G29


class VehicleController(ABC):
    @abstractmethod
    def tick(self):
        pass

    @abstractmethod
    def get_vehicle_control(self) -> carla.VehicleControl:
        pass

class ConstantVehicleController(VehicleController):
    def __init__(self, vehicle_control:carla.VehicleControl):
        self.vehicle_control = vehicle_control

    def tick(self):
        pass
    def get_vehicle_control(self) -> carla.VehicleControl:
        return self.vehicle_control

class G29Controller(VehicleController):
    def __init__(self, g29:G29):
        self.g29 = g29
        self.control = carla.VehicleControl()

    def tick(self):
        """このメソッドでは`g29.update()`を呼び出さないことに注意．
        別途`g29.update()`を呼び出すこと．
        理由としては，このクラス以外にも`g29`を使用するケースが想定され，
        このクラスに`g29.update()`を呼び出す責務があるのかどうかが不明確になるため．
        """
        self.control.throttle = self.g29.throttle_normalized
        self.control.brake = self.g29.brake_normalized
        self.control.steer = min(0.99, max(-0.99, self.g29.steering_rad * 0.2))

        # 後退
        if self.g29.is_triggered(G29.Button.Return):
            self.control.reverse = not self.control.reverse

    def get_vehicle_control(self) -> carla.VehicleControl:
        return self.control