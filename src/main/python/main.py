from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel, \
    QSlider, QCheckBox, QHBoxLayout, QComboBox, QLineEdit
from PyQt5.QtCore import Qt

import sys
import subprocess


class FFMPEG:
    def __init__(self):
        self.device_cmd = ['ffmpeg', '-list_devices', 'true', '-f', 'dshow',
                           '-i', 'dummy']
        self.stream_cmd_base = [
            'ffmpeg', '-re', '-f', 'lavfi', '-i',
            'color=size=640x480:rate=6:color=black'
        ]
        self.stream_audio_option = [
            '-ac', '2', '-c:a', 'aac', '-ar', '44100', '-b:a', '160k'
        ]
        self.amix_cmd = [
            '-filter_complex', 'amix=inputs=2:duration=longest'
        ]
        self.dshow_cmd = [
            '-f', 'dshow', '-i'
        ]
        self.rtmp_addr = 'rtmp://global-live.mux.com:5222/app/'

        self.current_stream = None

    def get_input_devices(self):
        proc = subprocess.run(self.device_cmd, stderr=subprocess.PIPE)
        result = proc.stderr.decode().split('\n')
        start_idx = -1
        for i, line in enumerate(result):
            if 'DirectShow audio devices' in line:
                start_idx = i
                break
        device_list = []
        for device in result[start_idx + 1:]:
            if 'dshow @' in device and 'Alternative' not in device:
                device_list.append(
                    device.split('  ')[-1].rstrip('\r').strip('"'))
        return device_list

    def start_streaming(self, key, input_device=None, system_device=None):
        cmd = self.stream_cmd_base
        if input_device:
            cmd += self.dshow_cmd
            cmd += [f'audio={input_device}']
        if system_device:
            cmd += self.dshow_cmd
            cmd += [f'audio={system_device}']
        if input_device and system_device:
            cmd += self.amix_cmd
        cmd += self.stream_audio_option
        cmd += ['-f', 'flv', f'{self.rtmp_addr}{key}']
        self.current_stream = subprocess.Popen(cmd, shell=True,
                                               stdin=subprocess.PIPE)

    def stop_streaming(self):
        self.current_stream.stdin.write(b'q')
        self.current_stream.kill()
        self.current_stream = None

    def adjust_mixer(self, *weights):
        self.current_stream.stdin.write(b'c')
        self.current_stream.stdin.write(
            f'amix -1 weights {weights[0]} {weights[1]}\n'.encode()
        )


class AppContext(ApplicationContext):
    def __init__(self):
        super().__init__()
        self.client = FFMPEG()

    def get_gain_pannel(self, title, root):
        layout = QHBoxLayout()
        layout.addWidget(QLabel(title))
        slider = QSlider(Qt.Horizontal)
        slider.setRange(1, 100)
        slider.setSingleStep(1)
        slider.setValue(100)
        layout.addWidget(slider)
        layout.addWidget(QLabel("Input Device"))
        device_box = QComboBox()
        device_box.addItems(self.client.get_input_devices())
        layout.addWidget(device_box)
        # layout.addWidget(QLabel('Enable: '))
        # layout.addWidget(QCheckBox())

        root.addLayout(layout)
        return slider, device_box

    def run(self):
        self.app.setStyle('Fusion')
        # Main Layout
        window = QWidget()
        window.resize(1020, 180)
        layout_main = QVBoxLayout()

        # Stream Key
        layout_key = QHBoxLayout()
        layout_key.addWidget(QLabel("Stream Key: "))
        key_field = QLineEdit()
        layout_key.addWidget(key_field)
        layout_main.addLayout(layout_key)

        # Sytem Sound Pannel
        system_gain, system_device = self.get_gain_pannel(
            'System Sound', layout_main)

        # Microphone Sound Panel
        mic_gain, mic_device = self.get_gain_pannel(
            'Microphone Input', layout_main)

        def adjust_mixer():
            self.client.adjust_mixer(
                mic_gain.value() / 100, system_gain.value() / 100
            )

        system_gain.valueChanged.connect(adjust_mixer)
        mic_gain.valueChanged.connect(adjust_mixer)

        # Stream Panel
        layout_stream = QHBoxLayout()
        stream_button = QPushButton("Start")
        stream_button.setFixedHeight(100)
        stop_button = QPushButton("Stop")
        stop_button.setFixedHeight(100)
        stop_button.setEnabled(False)

        def start_stream():
            stream_key = key_field.text()
            input_dev = mic_device.currentText()
            system_dev = system_device.currentText()
            self.client.start_streaming(stream_key, input_dev, system_dev)
            stream_button.setEnabled(False)
            stop_button.setEnabled(True)

        def stop_stream():
            self.client.stop_streaming()
            stop_button.setEnabled(False)
            stream_button.setEnabled(True)

        stop_button.clicked.connect(stop_stream)
        stream_button.clicked.connect(start_stream)

        layout_stream.addWidget(stream_button)
        layout_stream.addWidget(stop_button)
        layout_status = QVBoxLayout()
        layout_status.addWidget(QLabel("Status"))
        status_label = QLabel("")
        layout_status.addWidget(status_label)
        layout_stream.addLayout(layout_status)
        layout_main.addLayout(layout_stream)

        window.setLayout(layout_main)
        window.show()

        return self.app.exec_()


if __name__ == '__main__':
    appctxt = AppContext()      # 1. Instantiate ApplicationContext
    exit_code = appctxt.run()     # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)
