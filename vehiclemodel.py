from numpy import ndarray, sin, cos
import numpy as np

zeros = np.zeros
ones = np.ones
float64 = np.float64

# 先の調査で同定したもの．
DEFAULT_FRAMERATE = 25.0
DEFAULT_FRAMETIME = 1. / DEFAULT_FRAMERATE
DEFAULT_WHEELBASE = 13.90
DEFAULT_STEERING_SCALE = 1.022


class VehicleModel():
    def __init__(
            self,
            wheelbase: float = DEFAULT_WHEELBASE,
            steering_scale: float = DEFAULT_STEERING_SCALE,
            frame_time: float = DEFAULT_FRAMETIME
    ):
        self.wheelbase = wheelbase
        self.inv_wheelbase = 1. / wheelbase
        self.steering_scale = steering_scale
        self.frame_time = frame_time
        self.vts = .0
        self.speed_vts_div_wheelbase = 0.0

    def set_speed(self, speed: float):
        """速度を設定する．
        このモデルでは，速度のダイナミクスに関する記述はない．いわば，速度はパラメータとして扱われる．
        そして，モデルのダイナミクスを記述する際，速度が含まれる項が複雑（掛け算や割り算処理が含まれていて計算効率に支障がある）ため，
        その項を前もって計算しておく．
        """
        self.vts = speed * self.frame_time
        self.speed_vts_div_wheelbase = self.vts * self.inv_wheelbase

    def predict_constant_speed_variable_command_behaviour(
            self,
            initial_location_x: float,
            initial_location_y: float,
            initial_direction: float,
            commands_list: ndarray,
    ) -> tuple[ndarray, ndarray]:
        """
        速度は一定だが，ステアリング入力が時変の時の軌道を予測する．
        並列計算をして計算効率を上げるため，複数のサンプルを想定している．

        Parameters
        ----------
        initial_location_x:float
        initial_location_y:float
        initial_direction:float
        commands_list:ndarray
            （サンプルサイズ，ホライゾン）の行列形式．
            commands_list[i][k]には，サンプルiの予測ステップkにおけるステアリング入力の値を入れる．

        Returns
        -------
        x_history_list, y_history_list: tuple[ndarray, ndarray]
            どちらも（サンプルサイズ，ホライゾン+1）の行列形式．
            x_history_list[i][k]には，サンプルiの予測ステップkにおけるx座標の値が入る．
            y_history_listも同じ．
        """
        n_samples, horizon = commands_list.shape

        # メモリ参照先を密にするため[内部時間，サンプルインデックス]の順番で扱う
        commands_list_T = commands_list.T
        x_history_list_T = zeros(shape=(horizon + 1, n_samples), dtype=float64)
        y_history_list_T = zeros(shape=(horizon + 1, n_samples), dtype=float64)

        # 初期時刻
        x_history_list_T[0, :] = initial_location_x
        y_history_list_T[0, :] = initial_location_y
        direction_list = ones(shape=n_samples, dtype=float64) * initial_direction

        # 予測ステップ
        for command_list, inner_step in zip(commands_list_T, range(1, horizon + 1)):
            x_history_list_T[inner_step, :] = x_history_list_T[inner_step - 1, :] + self.vts * cos(direction_list)
            y_history_list_T[inner_step, :] = y_history_list_T[inner_step - 1, :] + self.vts * sin(direction_list)
            direction_list += self.speed_vts_div_wheelbase * command_list
        return (
            x_history_list_T.T,
            y_history_list_T.T
        )

    def predict_constant_speed_constant_command_behaviour(
            self,
            initial_location_x: float,
            initial_location_y: float,
            initial_direction: float,
            command: float,
            horizon: int,
            dtype: np.dtype = float64,
            state_history: ndarray | None = None
    ) -> ndarray:
        if state_history is None:
            state_history = zeros(shape=(horizon + 1, 3), dtype=dtype)
        x = initial_location_x
        y = initial_location_y
        phi = initial_direction

        state_history[0, 0] = x
        state_history[0, 1] = y
        state_history[0, 2] = phi
        for inner_step in range(1, horizon + 1):
            x += self.vts * cos(phi)
            y += self.vts * sin(phi)
            phi += self.speed_vts_div_wheelbase * command
            state_history[inner_step, 0] = x
            state_history[inner_step, 1] = y
            state_history[inner_step, 2] = phi
        return state_history

    def single_step(
            self,
            x, y, direction, command
    ) -> tuple[float, float, float]:
        next_x = x + self.vts * cos(direction)
        next_y = y + self.vts * sin(direction)
        next_direction = direction + self.speed_vts_div_wheelbase * command
        return next_x, next_y, next_direction
