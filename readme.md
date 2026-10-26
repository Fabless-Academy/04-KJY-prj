# TOPST Zonal Application

차량/보드의 영상 및 추론 결과를 받아 BEV(Bird's-Eye View) 차선·객체 정보를 계산하고, TOPST 대시보드와 차량 제어 인터페이스로 전달하는 애플리케이션입니다.

## 구성

- `Bridge_App/`: Python 브리지. 영상/추론 결과 수신, BEV 변환, 시나리오 재생, 대시보드 데이터 송신 및 선택적 MICOM 제어를 담당합니다.
- `TOPST_DashBoard/`: Qt Quick/Qt 3D 기반 대시보드 UI입니다.
- `split_out/`: 테스트 및 시나리오 영상 파일입니다.

브리지의 주요 데이터 흐름은 다음과 같습니다.

1. TCP 또는 Vision Protocol로 보드의 영상과 추론 결과를 수신합니다.
2. 서로 다른 호모그래피 설정을 적용해 대시보드 표시용 BEV와 차량 제어용 BEV를 생성합니다.
3. 차선, 객체, 경로 및 속도 추천 데이터를 대시보드에 전송합니다.
4. `--can-enable`을 지정하면 MICOM IPC를 통해 조향·속도·비상등 명령을 전송합니다.

대시보드 속도계의 시연용 속도는 50 km/h에서 시작해 0~70 km/h 범위의 목표값으로 천천히 변합니다. 이 표시용 속도는 MICOM 모터 명령과 별도이며, 모터 명령은 장애물 기반 `recommended_speed_kmh`를 사용합니다.

## 요구 사항

- Linux 환경
- Python 3
- Python 패키지: `numpy`, `opencv-python`
- Vision Protocol 모드 사용 시: 브리지에 포함된 `Bridge_App/bev_lane_modules/visionprotocol/`의 공유 라이브러리와 보드 연결 환경
- 대시보드 빌드 시: Qt 및 Qt Creator/qmake 개발 도구 (Qt Quick, Qt 3D 모듈 포함)

Python 패키지가 없다면 브리지 디렉터리에서 설치합니다.

```bash
python3 -m pip install numpy opencv-python
```

## 브리지 실행

먼저 브리지 디렉터리로 이동합니다. 설정 파일과 입력 영상 경로가 실행 위치 기준으로 해석되므로 이 위치에서 실행하는 것을 권장합니다.

```bash
cd Bridge_App
```

### Vision Protocol 연결

기본 전송 모드는 `vision`입니다. 공유 라이브러리는 브리지에 포함된 경로에서 먼저 찾습니다.

```bash
python3 zonal_app.py \
  --transport vision \
  --scenario-dir ../split_out \
  --video ../split_out/test_00.mp4
```

기본 Vision Protocol 포트는 스트림 `9998`, 메시지 `9999`입니다. 라이브러리를 다른 위치에서 찾아야 하는 경우 `--rtpm-root`에 해당 경로를 지정합니다.

### Raw TCP 연결

보드가 영상과 추론 결과를 TCP로 송신하는 경우 사용합니다.

```bash
python3 zonal_app.py \
  --transport tcp \
  --board-host 192.168.0.100 \
  --scenario-dir ../split_out \
  --video ../split_out/test_00.mp4
```

TCP 모드의 기본 보드 주소는 `192.168.0.100`이며 영상 포트는 `9999`, 추론 결과 포트는 `9998`입니다. 실제 보드 설정에 맞춰 `--board-host`, `--video-port`, `--result-port`를 변경하세요.

### 차량 제어 출력

기본 실행은 MICOM 제어를 활성화하지 않습니다. 장치와 권한을 확인한 후 다음 옵션을 추가합니다.

```bash
python3 zonal_app.py --can-enable --ipc-path /dev/tcc_ipc_micom
```

감속 권고 상태가 `slowing` 또는 `stop`이면 대시보드의 `BRAKE SIM` 표시와 MICOM 브레이크 LED를 켭니다. LED는 IPC 명령 ID `0x102`에 ON `0x01`, OFF `0x02`를 전송하며, 감속 권고가 해제되면 끕니다. 이 명령은 LED 표시만 제어하며 실제 제동 작동을 의미하지 않습니다.

## 주요 설정

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--transport` | `vision` | 보드 통신 방식: `vision` 또는 `tcp` |
| `--board-host` | `192.168.0.100` | Raw TCP 모드의 보드 IP |
| `--video-port` / `--result-port` | `9999` / `9998` | Raw TCP 영상 및 JSON 추론 결과 포트 |
| `--stream-port` / `--message-port` | `9998` / `9999` | Vision Protocol 스트림 및 메시지 포트 |
| `--qt-host` / `--qt-port` | `0.0.0.0` / `10000` | 대시보드 결과 수신 서버 주소 및 포트 |
| `--control-host` / `--control-port` | `0.0.0.0` / `10001` | 시나리오 선택 명령 수신 주소 및 포트 |
| `--scenario-dir` | `/home/ead/zonal_architecture/AI-G/split_out` | 재생 가능한 시나리오 영상 디렉터리 |
| `--video` | `output.mp4` | 시나리오 폴더에 선택 영상이 없을 때 사용할 영상 |
| `--display-homography` | `display_bev.json` | 대시보드용 BEV 변환 설정 |
| `--control-homography` | `control_bev.json` | 차량 제어용 BEV 변환 설정 |
| `--no-objects` | 꺼짐 | 객체 정보의 변환 및 전달 비활성화 |
| `--can-enable` | 꺼짐 | MICOM IPC 제어 출력 활성화 |

`display_bev.json`과 `control_bev.json`은 `Bridge_App/`에 있습니다. 시나리오 디렉터리 기본값은 이 저장소 경로가 아니므로, 저장소의 샘플 영상을 사용하려면 위 예제처럼 `--scenario-dir ../split_out`을 지정하세요.

`display_bev.json`과 `control_bev.json`은 각각 대시보드 표시와 차량 제어에 사용하는 BEV 캘리브레이션입니다. 선택한 영상이 캘리브레이션 기준 영상과 다르면 해당 용도에 맞는 좌표 보정이 필요합니다.

모든 브리지 옵션은 다음 명령으로 확인할 수 있습니다.

```bash
python3 zonal_app.py --help
```

## 대시보드 빌드 및 실행

대시보드 디렉터리에서 qmake로 빌드한 다음 실행합니다.

```bash
cd TOPST_DashBoard
qmake TOPST_DashBoard.pro
make
./TOPST_DashBoard
```

대시보드는 실행 디렉터리의 `config.json`에서 브리지 주소를 읽습니다. 기본 설정은 `127.0.0.1:10000`이며, 대시보드와 브리지가 다른 장비에서 실행될 때는 `server_ip`를 브리지의 IP 주소로 변경합니다. 시나리오 제어 포트는 기본값 `10001`이며, 변경할 경우 브리지의 `--control-port`와 대시보드 설정의 `control_port`를 동일하게 맞춥니다.

```json
{
  "server_ip": "127.0.0.1",
  "server_port": 10000,
  "control_port": 10001
}
```

## 테스트

브리지 디렉터리에서 단위 테스트를 실행합니다.

```bash
cd Bridge_App
python3 -m unittest discover -s tests
```
