from time import time
import math
import evdev
import rospy
from ctrl_pkg.msg import ServoCtrlMsg
from ctrl_pkg.srv import (ActiveStateSrv,
                          EnableStateSrv,
                          NavThrottleSrv)

ROS_RATE = 20   # 20hz
TIME_DIFF = 1.0/ROS_RATE
TIME_TO_STOP = 3 # 3 seconds to stop the motor
THROTTLE_MAX =  0.6

def scale(val, src, dst):
    return (float(val - src[0]) / (src[1] - src[0])) * (dst[1] - dst[0]) + dst[0]


def scale_stick(value):
    return scale(value, (0, 255), (-1.0, 1.0))


if __name__ == '__main__':
    rospy.init_node('gamepad_node', disable_signals=True)
    pub_manual_drive = rospy.Publisher('manual_drive', ServoCtrlMsg, queue_size=10)
    enable_state_req = rospy.ServiceProxy('enable_state', EnableStateSrv)
    msg = ServoCtrlMsg()
    # rate = rospy.Rate(ROS_RATE)
    devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
    gamepad = evdev.InputDevice(devices[0].fn)
    rospy.loginfo(gamepad)

    last_time = time() - TIME_DIFF
    angle = 0.0
    throttle = 0.0
    x_axis = 0.0
    y_axis = 0.0
    start_stop_state = False

    for event in gamepad.read_loop():
        # print(evdev.categorize(event))
        now = time()
        if now - last_time > TIME_TO_STOP and start_stop_state:
            start_stop_state = False
            enable_state_req(start_stop_state)
        if event.type == 3:      # Analog stick
            if not start_stop_state:
                start_stop_state = True
                enable_state_req(start_stop_state)
            if now - last_time < TIME_DIFF:
                continue
            if event.code == 0:  # X axis
                x_axis = scale_stick(event.value)
                angle = - x_axis
            if event.code == 1:  # Y axis
                y_axis = scale_stick(event.value)
                throttle = min(1.0, math.sqrt(y_axis*y_axis + x_axis*x_axis))
                throttle = - math.copysign(throttle, y_axis)
            if event.code == 0 or event.code == 1:
                try:
                    if not rospy.is_shutdown():
                        msg.angle = angle
                        msg.throttle = THROTTLE_MAX * throttle
                        pub_manual_drive.publish(msg)
                        rospy.loginfo(msg)
                        last_time = now
                except rospy.ROSInterruptException:
                    print("ROS exit")
                    exit(0)
