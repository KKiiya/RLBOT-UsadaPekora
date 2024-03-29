from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3


class MyBot(BaseAgent):
    is_flying = False

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """

        # Keep our boost pad info updated with which pads are currently active
        self.boost_pad_tracker.update_boost_status(packet)

        # This is good to keep at the beginning of get_output. It will allow you to continue
        # any sequences that you may have started during a previous call to get_output.
        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls

        # Gather some information about our car and the ball
        my_car = packet.game_cars[self.index]
        my_team = self.team
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_future_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)

        if car_location.dist(ball_location) > 1500:
            # We're far away from the ball, let's try to lead it a little bit
            ball_prediction = self.get_ball_prediction_struct()  # This can predict bounces, etc
            ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + 1)

            # ball_in_future might be None if we don't have an adequate ball prediction right now, like during
            # replays, so check it to avoid errors.
            if ball_in_future is not None:
                ball_future_location = Vec3(ball_in_future.physics.location)
                target_location = ball_future_location
                # self.renderer.draw_line_3d(ball_location, target_location, self.renderer.cyan())

        # Draw some things to help understand what the bot is thinking
        # self.renderer.draw_line_3d(car_location, target_location, self.renderer.white())
        # self.renderer.draw_string_3d(car_location, 1, 1, f'Speed: {car_velocity.length():.1f}', self.renderer.white())
        # self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)

        # if 750 < car_velocity.length() < 800:
        # We'll do a front flip if the car is moving at a certain speed.
        # return self.begin_front_flip(packet)

        # You can set more controls if you want, like controls.boost.
        controls = SimpleControllerState()
        """
        nearest_pad = None
        if my_car.boost < 10:
            for pad in self.boost_pad_tracker.boost_pads:
                if pad.is_active:
                    self.boost_pad_tracker.boost_pads.sort(key=lambda x: x.location.dist(car_location))
                    nearest_pad = self.boost_pad_tracker.boost_pads[0]
                    break

            if nearest_pad is not None and nearest_pad.is_full_boost:
                controls.steer = steer_toward_target(my_car, nearest_pad.location)

            if car_location.dist(nearest_pad.location) > 1000:
                controls.throttle = 0.5
                controls.boost = False
            else:
                controls.throttle = 0.3
                controls.boost = False
        else:
            controls.steer = steer_toward_target(my_car, ball_future_location)
            controls.throttle = 1
            controls.boost = False
        """

        self.wall_dash_left(packet)

        """
        if (ball_velocity.length() > car_velocity.length() + 100):
            if (my_car.boost > 25):
                if (car_location.dist(ball_future_location) < 1500):
                    if (my_car.jumped):
                        controls.boost = True
                        controls.throttle = 1
                    else:
                        self.startAerial(packet)
                else:
                    self.begin_front_flip(packet)
        """

        return controls

    def begin_front_flip(self, packet):
        # Send some quick chat just for fun
        # self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Reactions_Okay)

        # Do a front flip. We will be committed to this for a few seconds and the bot will ignore other
        # logic during that time because we are setting the active_sequence.
        self.active_sequence = Sequence([
            ControlStep(duration=0.02, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(duration=0.8, controls=SimpleControllerState()),
        ])

        # Return the controls associated with the beginning of the sequence, so we can start right away.
        return self.active_sequence.tick(packet)

    def startAerial(self, packet: GameTickPacket):
        my_car = packet.game_cars[self.index]

        self.active_sequence = Sequence([
            ControlStep(duration=0.02, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(steer=-1.0, jump=True)),
            ControlStep(duration=1, controls=SimpleControllerState(boost=True, pitch=1)),
        ])

        return self.active_sequence.tick(packet)

    def speedFlip(self, packet: GameTickPacket):
        my_car = packet.game_cars[self.index]

        self.active_sequence = Sequence([
            ControlStep(duration=0.01, controls=SimpleControllerState(boost=True)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.03, controls=SimpleControllerState(steer=-1.0, jump=True)),
            ControlStep(duration=1, controls=SimpleControllerState(boost=True, pitch=1)),
        ])

        return self.active_sequence.tick(packet)

    def zap_dash(self, packet: GameTickPacket):
        my_car = packet.game_cars[self.index]

        self.active_sequence = Sequence([
            ControlStep(duration=0.2, controls=SimpleControllerState(throttle=-1, pitch=1)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=True, pitch=1)),
            ControlStep(duration=1, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=True, pitch=-1, throttle=1)),
        ])

    def half_flip(self, packet: GameTickPacket):
        my_car = packet.game_cars[self.index]

        self.active_sequence = Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(throttle=-1)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=True, pitch=1)),
            ControlStep(duration=0.05, controls=SimpleControllerState(pitch=-1)),


        ])

        return self.active_sequence.tick(packet)

    def wall_dash_left(self, packet: GameTickPacket):
        my_car = packet.game_cars[self.index]

        self.active_sequence = Sequence([
            ControlStep(duration=0.2, controls=SimpleControllerState(throttle=1)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=True, throttle=1)),
            ControlStep(duration=0.001, controls=SimpleControllerState(jump=False, roll=-1, throttle=1)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=True, roll=-1, throttle=1)),
        ])

        return self.active_sequence.tick(packet)
