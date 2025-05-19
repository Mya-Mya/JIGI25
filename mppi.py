from vehiclemodel import VehicleModel
from numpy import ndarray, exp, sum, zeros_like, bool_, square, exp, any
from numpy import array as npa
from numpy.random import randn
from enum import Enum
from typing import Optional
from dataclasses import dataclass
from keepoutareas import KeepoutArea


class FilteringFlow(Enum):
    """MPPI介入制御器において，どのようなフィルタリングが行われたかを記述する．"""
    # そもそも立ち入り禁止領域が無かった（ためノミナル入力をそのまま通す）．
    NoKeepoutArea = "NoKeepoutArea"
    # ノミナル入力は立ち入り禁止領域を冒進しないと判断された（ためノミナル入力をそのまま通す）．
    NoIntervention = "NoIntervention"
    # ノミナル入力は立ち入り禁止領域を冒進すると判断された（ため介入入力を出力する）．
    Intervention = "Intervention"


@dataclass
class MPPIFilterResult:
    """MPPI介入制御器の出力を記述する．"""
    # フィルタされた後のステアリング入力．
    filtered_command: float
    # どのようなフィルタリングが行われたか．
    flow: FilteringFlow
    # ノミナル入力のまま進行した時の予測軌道
    nominal_x_history: Optional[ndarray] = None
    nominal_y_history: Optional[ndarray] = None
    # サンプリングによって生成されたステアリング入力候補
    commands_list: Optional[ndarray] = None
    # 各ステアリング入力候補に対する予測軌道
    x_history_list: Optional[ndarray] = None
    y_history_list: Optional[ndarray] = None
    # 各ステアリング入力候補に対する重み
    sample_weights: Optional[ndarray] = None


class MPPIFilter():
    def __init__(
            self,
            vehiclemodel: VehicleModel,
            samplesize: int,
            horizon: int,
            command_lb: float = -1.0,
            command_ub: float = 1.0,
            command_std: float = 0.5,
            violation_weight: float = 1000.,
            violation_weight_decay: float = 0.90,
            temperature: float = 1.0
    ):
        """
        MPPI介入制御器．

        Parameters
        ----------
        vehiclemodel:VehicleModel
            制御器内部で軌道予測に使う内部モデル．
        samplesize:int
            ステアリング入力サンプルの数．
        horizon:int
            予測ホライズン．
        command_lb:float
            ステアリング入力サンプルの下限．
        command_ub:float
            ステアリング入力サンプルの上限．
        command_std:float
            ステアリング入力サンプルの標準偏差．
        violation_weight:float
            立ち入り禁止領域への冒進時のコスト．
        violation_weight_decay:float
            立ち入り禁止領域への冒進時のコストを，予測ステップが進むごとに減衰させていく係数．
        temperature:float
            ステアリング入力を決定する際の温度パラメータ．
        """
        self.vehiclemodel = vehiclemodel
        self.samplesize = samplesize
        self.horizon = horizon
        self.command_lb = command_lb
        self.command_ub = command_ub
        self.command_std = command_std
        self.command_var = command_std * command_std
        self.violation_weight = violation_weight
        self.violation_weight_decay = violation_weight_decay
        self.temperature = temperature

        self.keepoutareas: list[KeepoutArea] = []
        self.violation_weights = npa([
            violation_weight * violation_weight_decay ** step
            for step in range(horizon + 1)
        ])
        self.previous_optimal_command = 0.

    def set_keepoutareas(self, keepoutareas: list[KeepoutArea]):
        self.keepoutareas = keepoutareas

    def prepare_for_filtering(self, speed: float):
        self.vehiclemodel.set_speed(speed)

    def generate_commands_samples(self, mean: float) -> ndarray:
        commands_samples = randn(self.samplesize, self.horizon) * self.command_std + mean
        commands_samples[commands_samples >= self.command_ub] = self.command_ub
        commands_samples[commands_samples <= self.command_lb] = self.command_lb
        return commands_samples

    def check_all_keepoutareas(self, x: ndarray, y: ndarray) -> ndarray[bool]:
        """
        x,yがいずれかの立ち入り禁止領域に入っていないかを要素ごとに調べる．
        立ち入り禁止領域に入っている場合，対応する要素をTrueにして返す．
        xとyはベクトルでも行列でも可．
        """
        violates = zeros_like(x, dtype=bool_)
        violates = False
        for koa in self.keepoutareas:
            violates_koa = koa.check(x, y) <= 0
            violates = violates + violates_koa  # 和論理を取る
        return violates

    def get_filtered_command(
            self,
            initial_location_x: float,
            initial_location_y: float,
            initial_direction: float,
            initial_speed: float,
            nominal_command: float,
            commands_list: ndarray | None = None
    ) -> MPPIFilterResult:
        """
        MPPI介入制御器を動かす．

        Parameters
        ----------
        initial_location_x:float
        initial_location_y:float
        initial_direction:float
        initial_speed:float
        nominal_command:float
            ノミナル入力．運転者によるステアリング入力を想定している．
            0などの定数に設定することで，自動運転タスクなどに使うこともできる．
        commands_list:ndarray|None=None
            （任意）ステアリング入力のサンプル．

        Returns
        -------
        result:MPPIFilterResult
            当制御器の出力を表すオブジェクト．
        """
        # 立ち入り禁止領域が無ければ介入の必要はない
        if not self.keepoutareas:
            self.previous_optimal_command = nominal_command
            return MPPIFilterResult(
                filtered_command=nominal_command,
                flow=FilteringFlow.NoKeepoutArea
            )

        # モデルによる計算準備
        self.prepare_for_filtering(initial_speed)

        # ノミナル入力が立ち入り禁止領域に入らないかを判断する
        nominal_state_history = self.vehiclemodel.predict_constant_speed_constant_command_behaviour(
            initial_location_x=initial_location_x,
            initial_location_y=initial_location_y,
            initial_direction=initial_direction,
            command=nominal_command,
            horizon=self.horizon,
        )
        nominal_x_history = nominal_state_history[:, 0]
        nominal_y_history = nominal_state_history[:, 1]
        violates = self.check_all_keepoutareas(nominal_x_history, nominal_y_history)
        if not any(violates):
            # 立ち入り禁止エリアに入らない
            self.previous_optimal_command = nominal_command
            return MPPIFilterResult(
                filtered_command=nominal_command,
                flow=FilteringFlow.NoIntervention,
                nominal_x_history=nominal_x_history,
                nominal_y_history=nominal_y_history
            )

        # 立ち入り禁止エリアに入るため介入が必要！
        if commands_list is None:
            commands_list = self.generate_commands_samples(self.previous_optimal_command)
        x_history_list, y_history_list = \
            self.vehiclemodel.predict_constant_speed_variable_command_behaviour(
                initial_location_x=initial_location_x,
                initial_location_y=initial_location_y,
                initial_direction=initial_direction,
                commands_list=commands_list
            )

        # 立ち入り禁止領域冒進に対するコスト
        violates_history_list = self.check_all_keepoutareas(x_history_list, y_history_list)  # （サンプルサイズ，ホライズン+1）
        violation_cost_list = sum(violates_history_list * self.violation_weights, axis=1)  # （サンプルサイズ，）

        # 入力コスト
        commands_cost_list = sum(square(commands_list - nominal_command) / self.command_var, axis=1)

        # 分配率を計算する
        exp_inner = - violation_cost_list / self.temperature - commands_cost_list
        exp_inner -= exp_inner.max()
        exp_outer = exp(exp_inner)
        sample_weights = exp_outer / sum(exp_outer)

        # 最適コストを決定する
        step0_command_list = commands_list[:, 0]
        optimal_command = sum(step0_command_list * sample_weights)

        self.previous_optimal_command = optimal_command
        return MPPIFilterResult(
            filtered_command=optimal_command,
            flow=FilteringFlow.Intervention,
            nominal_x_history=nominal_x_history,
            nominal_y_history=nominal_y_history,
            commands_list=commands_list,
            x_history_list=x_history_list,
            y_history_list=y_history_list,
            sample_weights=sample_weights
        )
