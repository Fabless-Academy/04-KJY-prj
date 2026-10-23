import QtQuick 2.12
import QtQuick.Scene3D 2.12
import Qt3D.Core 2.12
import Qt3D.Extras 2.12
import Qt3D.Input 2.12
import Qt3D.Render 2.12
import Zonal 1.0

Scene3D {
    id: root

    // Python 브리지에서 전달한 BEV 데이터와 3D 장면 스케일 설정값들이다.
    property var bevObjects: []
    property var lanePolylines: [[], [], [], []]
    property var laneModel: ({})
    property int laneFrameWidth: 800
    property int laneFrameHeight: 480
    property real worldRoadWidth: 30.0
    property real worldRoadZMin: -32.0
    property real worldRoadDepth: 50.0
    property real roadY: -0.92
    property real egoVehicleZ: 11.5
    property int laneCurveSegments: 48
    property int pathCurveSegments: 20
    property real egoPathWidthRatio: 0.46
    property bool showPath: true

    anchors.fill: parent
    anchors.margins: 0
    aspects: ["input", "logic", "render"]

    function objectAt(index) {
        return index < root.bevObjects.length ? root.bevObjects[index] : null
    }

    function laneAt(index) {
        var lane = index < root.lanePolylines.length ? root.lanePolylines[index] : []
        return lane && lane.length !== undefined ? lane : []
    }

    function centerline() {
        // centerline이 별도로 오면 그것을 쓰고, 없으면 ego 좌우 차선의 중점으로 구성한다.
        if (root.laneModel && root.laneModel.centerline)
            return root.laneModel.centerline
        var left = root.laneAt(1)
        var right = root.laneAt(2)
        var count = Math.min(left.length, right.length)
        var pts = []
        for (var i = 0; i < count; ++i) {
            pts.push({
                x: (Number(left[i].x) + Number(right[i].x)) * 0.5,
                y: (Number(left[i].y) + Number(right[i].y)) * 0.5
            })
        }
        return pts
    }

    function rawPath() {
        // raw_path는 planning 결과이며, 없으면 빈 경로로 처리한다.
        if (root.laneModel && root.laneModel.raw_path)
            return root.laneModel.raw_path
        return []
    }

    // 2D BEV 픽셀 좌표를 3D 월드 x/z 축 좌표로 선형 변환한다.
    function bevToWorldX(bevX) {
        var xNorm = Number(bevX) / Math.max(1, root.laneFrameWidth)
        return (xNorm - 0.5) * root.worldRoadWidth
    }

    function bevToWorldZ(bevY) {
        var yNorm = Number(bevY) / Math.max(1, root.laneFrameHeight)
        return root.worldRoadZMin + yNorm * root.worldRoadDepth
    }

    function pointToWorld(point, yValue) {
        return {
            x: bevToWorldX(point.x !== undefined ? point.x : point.bev_x),
            y: yValue !== undefined ? yValue : root.roadY,
            z: bevToWorldZ(point.y !== undefined ? point.y : point.bev_y)
        }
    }

    function clampIndex(value, minValue, maxValue) {
        return Math.max(minValue, Math.min(maxValue, value))
    }

    function catmullRom(p0, p1, p2, p3, t) {
        var t2 = t * t
        var t3 = t2 * t
        return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)
    }

    function sampledCurvePoint(points, uNorm, yValue) {
        // 차선/경로 점들을 Catmull-Rom 곡선으로 샘플링해 리본이 부드럽게 보이게 한다.
        if (!points || points.length === 0)
            return { x: 0, y: yValue, z: -1000 }
        if (points.length === 1)
            return pointToWorld(points[0], yValue)
        var u = Math.max(0.0, Math.min(1.0, uNorm)) * (points.length - 1)
        var i = Math.floor(u)
        var t = u - i
        var i0 = clampIndex(i - 1, 0, points.length - 1)
        var i1 = clampIndex(i, 0, points.length - 1)
        var i2 = clampIndex(i + 1, 0, points.length - 1)
        var i3 = clampIndex(i + 2, 0, points.length - 1)
        var p0 = pointToWorld(points[i0], yValue)
        var p1 = pointToWorld(points[i1], yValue)
        var p2 = pointToWorld(points[i2], yValue)
        var p3 = pointToWorld(points[i3], yValue)
        return {
            x: catmullRom(p0.x, p1.x, p2.x, p3.x, t),
            y: yValue,
            z: catmullRom(p0.z, p1.z, p2.z, p3.z, t)
        }
    }

    function sampledWorldPoints(points, segments, yValue) {
        var out = []
        if (!points || points.length < 2)
            return out
        for (var i = 0; i <= segments; ++i)
            out.push(sampledCurvePoint(points, i / Math.max(1, segments), yValue))
        return out
    }

    function laneRibbonPoints(laneIndex) {
        return sampledWorldPoints(laneAt(laneIndex), root.laneCurveSegments, root.roadY + 0.05)
    }

    function laneBoundaryPoints(laneIndex, yValue) {
        return sampledWorldPoints(laneAt(laneIndex), root.laneCurveSegments, yValue)
    }

    function rawPathRibbonPoints() {
        var pts = rawPath()
        if (pts.length < 2)
            return []
        return sampledWorldPoints(pts, Math.max(pts.length - 1, 1), root.roadY + 0.035)
    }

    function laneWidth(index) {
        return (index === 1 || index === 2) ? 0.18 : 0.12
    }

    function laneColor(index) {
        return (index === 1 || index === 2) ? "#f7fbff" : "#b7c3cc"
    }

    function egoLaneWorldWidth() {
        // lane_model 폭 정보가 있으면 우선 사용하고, 없으면 좌우 차선 간 거리로 추정한다.
        if (root.laneModel && root.laneModel.valid && root.laneModel.lane_width_px)
            return Math.max(2.2, (Number(root.laneModel.lane_width_px) / Math.max(1, root.laneFrameWidth)) * root.worldRoadWidth)
        var left = laneAt(1)
        var right = laneAt(2)
        if (left.length > 0 && right.length > 0) {
            var a = pointToWorld(left[0], root.roadY)
            var b = pointToWorld(right[0], root.roadY)
            return Math.max(2.2, Math.abs(b.x - a.x))
        }
        return 2.6
    }

    function egoPathWidth() {
        return egoLaneWorldWidth() * root.egoPathWidthRatio
    }

    function headingPathWorldPoints() {
        var pts = rawPath()
        if (pts.length >= 2)
            return sampledWorldPoints(pts, Math.max(pts.length - 1, 1), root.roadY)
        pts = centerline()
        if (pts.length >= 2)
            return sampledWorldPoints(pts, Math.max(root.pathCurveSegments, pts.length - 1), root.roadY)
        return []
    }

    function egoVehicleYaw() {
        // ego 차량 yaw는 현재 경로의 접선 방향을 따라가도록 계산한다.
        var pts = headingPathWorldPoints()
        if (pts.length < 2)
            return 90.0

        var bestIndex = 0
        var bestDistance = Math.abs(Number(pts[0].z) - root.egoVehicleZ)
        for (var i = 1; i < pts.length; ++i) {
            var dist = Math.abs(Number(pts[i].z) - root.egoVehicleZ)
            if (dist < bestDistance) {
                bestDistance = dist
                bestIndex = i
            }
        }

        var prevIndex = Math.max(0, bestIndex - 1)
        var nextIndex = Math.min(pts.length - 1, bestIndex + 1)
        if (prevIndex === nextIndex)
            return 90.0

        var dx = Number(pts[nextIndex].x) - Number(pts[prevIndex].x)
        var dz = Number(pts[nextIndex].z) - Number(pts[prevIndex].z)
        if (Math.abs(dx) < 0.0001 && Math.abs(dz) < 0.0001)
            return 90.0

        return 90.0 + Math.atan2(dx, dz) * 180.0 / Math.PI
    }

    function objectToWorld(point) {
        return { x: bevToWorldX(point.bev_x), z: bevToWorldZ(point.bev_y) }
    }

    function objectYaw(point) {
        var laneId = Number(point.lane_id)
        if (laneId === 1) return 90.0
        var xNorm = Number(point.bev_x) / Math.max(1, root.laneFrameWidth)
        return 90.0 + (xNorm - 0.5) * 16.0
    }

    function objectScale(point) {
        var yNorm = Number(point.bev_y) / Math.max(1, root.laneFrameHeight)
        return 0.027 + yNorm * 0.005
    }

    function objectAvailable(index) { return objectAt(index) !== null }

    function objectWorld(index) {
        var obj = objectAt(index)
        if (!obj) return { x: 0, z: -1000 }
        return objectToWorld(obj)
    }

    function objectWorldScale(index) {
        var obj = objectAt(index)
        return obj ? objectScale(obj) : 0.0001
    }

    function objectWorldYaw(index) {
        var obj = objectAt(index)
        return obj ? objectYaw(obj) : 90.0
    }

    function objectDepthAlpha(index) {
        var obj = objectAt(index)
        if (!obj) return 0
        var yNorm = Number(obj.bev_y) / Math.max(1, root.laneFrameHeight)
        return Math.max(0.15, Math.min(1.0, yNorm * 1.4))
    }

    Entity {
        id: sceneRoot

        Camera {
            id: camera
            position: Qt.vector3d(0, 13, 34)
            viewCenter: Qt.vector3d(0, -1.2, -2)
            upVector: Qt.vector3d(0, 1, 0)
        }

        components: [
            RenderSettings {
                activeFrameGraph: ForwardRenderer {
                    camera: camera
                    clearColor: "#0a1220"
                }
            },
            InputSettings {}
        ]

        // 여러 방향 조명을 겹쳐 평면적인 장면을 피하고 깊이감을 만든다.
        Entity {
            components: [
                DirectionalLight {
                    worldDirection: Qt.vector3d(-0.3, -1.0, -0.3)
                    color: "#dce8f4"
                    intensity: 0.75
                }
            ]
        }
        Entity {
            components: [
                DirectionalLight {
                    worldDirection: Qt.vector3d(0.4, -0.3, 0.5)
                    color: "#2060a0"
                    intensity: 0.3
                }
            ]
        }
        Entity {
            components: [
                DirectionalLight {
                    worldDirection: Qt.vector3d(0, 0.1, -1.0)
                    color: "#102040"
                    intensity: 0.2
                }
            ]
        }
        Entity {
            components: [
                DirectionalLight {
                    worldDirection: Qt.vector3d(0, -0.8, 0.3)
                    color: "#40608a"
                    intensity: 0.15
                }
            ]
        }

        // 하늘 배경 plane을 여러 장 겹쳐 상단/중단/하단 색감을 분리한다.
        Entity {
            components: [
                PlaneMesh { width: 300; height: 120 },
                PhongMaterial {
                    diffuse: "#101828"
                    ambient: "#0e1624"
                    specular: "#000000"
                    shininess: 0
                },
                Transform {
                    translation: Qt.vector3d(0, 28, -90)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -25)
                }
            ]
        }

        // === SKY: mid sky (blue-purple) ===
        Entity {
            components: [
                PlaneMesh { width: 300; height: 50 },
                PhongMaterial {
                    diffuse: "#1a2844"
                    ambient: "#162240"
                    specular: "#182640"
                    shininess: 0
                },
                Transform {
                    translation: Qt.vector3d(0, 12, -85)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -18)
                }
            ]
        }

        // === SKY: low sky (warm twilight) ===
        Entity {
            components: [
                PlaneMesh { width: 300; height: 30 },
                PhongMaterial {
                    diffuse: "#263c58"
                    ambient: "#203450"
                    specular: "#2a4060"
                    shininess: 1
                },
                Transform {
                    translation: Qt.vector3d(0, 4, -80)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -10)
                }
            ]
        }

        // === HORIZON GLOW: wide warm band ===
        Entity {
            components: [
                PlaneMesh { width: 300; height: 8 },
                PhongMaterial {
                    diffuse: "#4a6a88"
                    ambient: "#3e5c78"
                    specular: "#6888a8"
                    shininess: 10
                },
                Transform {
                    translation: Qt.vector3d(0, 0.8, -75)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -4)
                }
            ]
        }

        // === HORIZON GLOW: bright core strip ===
        Entity {
            components: [
                PlaneMesh { width: 220; height: 3.5 },
                PhongMaterial {
                    diffuse: "#6890b0"
                    ambient: "#5878a0"
                    specular: "#88aac8"
                    shininess: 15
                },
                Transform {
                    translation: Qt.vector3d(0, 0.3, -73)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -3)
                }
            ]
        }

        // === HORIZON GLOW: hottest center line ===
        Entity {
            components: [
                PlaneMesh { width: 140; height: 1.8 },
                PhongMaterial {
                    diffuse: "#88a8c8"
                    ambient: "#78a0c0"
                    specular: "#a0c0e0"
                    shininess: 20
                },
                Transform {
                    translation: Qt.vector3d(0, 0.05, -71)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -2)
                }
            ]
        }

        // === HORIZON: ground-sky transition ===
        Entity {
            components: [
                PlaneMesh { width: 300; height: 15 },
                PhongMaterial {
                    diffuse: "#1e3048"
                    ambient: "#182840"
                    specular: "#283c54"
                    shininess: 3
                },
                Transform {
                    translation: Qt.vector3d(0, -0.6, -65)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -2)
                }
            ]
        }

        // === GROUND: far terrain ===
        Entity {
            components: [
                PlaneMesh { width: 160; height: 100 },
                PhongMaterial {
                    diffuse: "#0c1620"
                    ambient: "#081018"
                    specular: "#0e1a28"
                    shininess: 1
                },
                Transform {
                    translation: Qt.vector3d(0, -1.08, -30)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -90)
                }
            ]
        }

        // === ROAD: multi-layer asphalt ===
        Entity {
            components: [
                PlaneMesh { width: 34; height: 112 },
                PhongMaterial {
                    diffuse: "#1a2632"
                    ambient: "#14202c"
                    specular: "#283c50"
                    shininess: 8
                },
                Transform {
                    translation: Qt.vector3d(0, -1.0, 0)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -90)
                }
            ]
        }
        Entity {
            components: [
                PlaneMesh { width: 18; height: 112 },
                PhongMaterial {
                    diffuse: "#1e2e3c"
                    ambient: "#182838"
                    specular: "#2e4258"
                    shininess: 10
                },
                Transform {
                    translation: Qt.vector3d(0, -0.98, 0)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -90)
                }
            ]
        }

        // === ROAD: shoulder lines (outer edges) ===
        Entity {
            components: [
                PlaneMesh { width: 0.15; height: 90 },
                PhongMaterial {
                    diffuse: "#384858"
                    ambient: "#303e50"
                    specular: "#5a6a7a"
                    shininess: 12
                },
                Transform {
                    translation: Qt.vector3d(-8.8, -0.96, -5)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -90)
                }
            ]
        }
        Entity {
            components: [
                PlaneMesh { width: 0.15; height: 90 },
                PhongMaterial {
                    diffuse: "#384858"
                    ambient: "#303e50"
                    specular: "#5a6a7a"
                    shininess: 12
                },
                Transform {
                    translation: Qt.vector3d(8.8, -0.96, -5)
                    rotation: fromAxisAndAngle(Qt.vector3d(1, 0, 0), -90)
                }
            ]
        }

        // === ROAD: center dashed line ===
        Entity { components: [ PlaneMesh { width: 0.12; height: 3.5 }, PhongMaterial { diffuse: "#4a5a6a"; ambient: "#3a4a5a"; shininess: 8 }, Transform { translation: Qt.vector3d(0, -0.96, 18); rotation: fromAxisAndAngle(Qt.vector3d(1,0,0), -90) } ] }
        Entity { components: [ PlaneMesh { width: 0.12; height: 3.5 }, PhongMaterial { diffuse: "#4a5a6a"; ambient: "#3a4a5a"; shininess: 8 }, Transform { translation: Qt.vector3d(0, -0.96, 9.5); rotation: fromAxisAndAngle(Qt.vector3d(1,0,0), -90) } ] }
        Entity { components: [ PlaneMesh { width: 0.12; height: 3.5 }, PhongMaterial { diffuse: "#4a5a6a"; ambient: "#3a4a5a"; shininess: 8 }, Transform { translation: Qt.vector3d(0, -0.96, 1); rotation: fromAxisAndAngle(Qt.vector3d(1,0,0), -90) } ] }
        Entity { components: [ PlaneMesh { width: 0.12; height: 3.5 }, PhongMaterial { diffuse: "#4a5a6a"; ambient: "#3a4a5a"; shininess: 8 }, Transform { translation: Qt.vector3d(0, -0.96, -7.5); rotation: fromAxisAndAngle(Qt.vector3d(1,0,0), -90) } ] }
        Entity { components: [ PlaneMesh { width: 0.12; height: 3.5 }, PhongMaterial { diffuse: "#4a5a6a"; ambient: "#3a4a5a"; shininess: 8 }, Transform { translation: Qt.vector3d(0, -0.96, -16); rotation: fromAxisAndAngle(Qt.vector3d(1,0,0), -90) } ] }
        Entity { components: [ PlaneMesh { width: 0.12; height: 3.5 }, PhongMaterial { diffuse: "#4a5a6a"; ambient: "#3a4a5a"; shininess: 8 }, Transform { translation: Qt.vector3d(0, -0.96, -24.5); rotation: fromAxisAndAngle(Qt.vector3d(1,0,0), -90) } ] }
        Entity { components: [ PlaneMesh { width: 0.12; height: 3.5 }, PhongMaterial { diffuse: "#3a4a5a"; ambient: "#2a3a4a"; shininess: 6 }, Transform { translation: Qt.vector3d(0, -0.96, -33); rotation: fromAxisAndAngle(Qt.vector3d(1,0,0), -90) } ] }
        Entity { components: [ PlaneMesh { width: 0.12; height: 3.5 }, PhongMaterial { diffuse: "#3a4a5a"; ambient: "#2a3a4a"; shininess: 6 }, Transform { translation: Qt.vector3d(0, -0.96, -41.5); rotation: fromAxisAndAngle(Qt.vector3d(1,0,0), -90) } ] }

        // === EGO VEHICLE LIGHTING: headlight glow ===
        Entity {
            components: [
                PointLight {
                    color: "#80ccff"
                    intensity: 0.55
                    constantAttenuation: 1.0
                    linearAttenuation: 0.015
                    quadraticAttenuation: 0.001
                },
                Transform { translation: Qt.vector3d(0, 1.5, 16) }
            ]
        }
        Entity {
            components: [
                PointLight {
                    color: "#59c0cd"
                    intensity: 0.25
                    constantAttenuation: 1.0
                    linearAttenuation: 0.05
                    quadraticAttenuation: 0.005
                },
                Transform { translation: Qt.vector3d(0, -0.5, 8) }
            ]
        }
        Entity {
            components: [
                PointLight {
                    color: "#203050"
                    intensity: 0.2
                    constantAttenuation: 1.0
                    linearAttenuation: 0.04
                    quadraticAttenuation: 0.004
                },
                Transform { translation: Qt.vector3d(0, 5, -10) }
            ]
        }

        // === HORIZON GLOW LIGHTING ===
        Entity {
            components: [
                PointLight {
                    color: "#7090b8"
                    intensity: 0.8
                    constantAttenuation: 1.0
                    linearAttenuation: 0.005
                    quadraticAttenuation: 0.0003
                },
                Transform { translation: Qt.vector3d(0, 3, -60) }
            ]
        }
        Entity {
            components: [
                PointLight {
                    color: "#5878a0"
                    intensity: 0.5
                    constantAttenuation: 1.0
                    linearAttenuation: 0.006
                    quadraticAttenuation: 0.0004
                },
                Transform { translation: Qt.vector3d(-25, 2, -55) }
            ]
        }
        Entity {
            components: [
                PointLight {
                    color: "#5878a0"
                    intensity: 0.5
                    constantAttenuation: 1.0
                    linearAttenuation: 0.006
                    quadraticAttenuation: 0.0004
                },
                Transform { translation: Qt.vector3d(25, 2, -55) }
            ]
        }
        Entity {
            components: [
                DirectionalLight {
                    color: "#405878"
                    intensity: 0.3
                    worldDirection: Qt.vector3d(0, -0.3, 1)
                },
                Transform { translation: Qt.vector3d(0, 10, -70) }
            ]
        }

        // === LANE CORRIDORS (road surface between lanes) ===
        Entity {
            // Path 토글은 별도 리본이 아니라 현재 ego 차선 corridor 표시 on/off로 사용한다.
            enabled: root.showPath
                     && root.laneBoundaryPoints(1, root.roadY + 0.012).length > 1
                     && root.laneBoundaryPoints(2, root.roadY + 0.012).length > 1
            components: [
                LaneCorridorMesh {
                    leftPoints: root.laneBoundaryPoints(1, root.roadY + 0.012)
                    rightPoints: root.laneBoundaryPoints(2, root.roadY + 0.012)
                },
                PhongMaterial { diffuse: "#2c4259"; ambient: "#24384d"; specular: "#4a7eb3"; shininess: 10 }
            ]
        }

        // === LANE LINES (glowing cyan/blue) ===
        Entity {
            enabled: root.laneRibbonPoints(0).length > 1
            components: [
                LaneRibbonMesh { points: root.laneRibbonPoints(0); width: root.laneWidth(0) },
                PhongMaterial {
                    diffuse: root.laneColor(0)
                    ambient: root.laneColor(0)
                    specular: "#eef5fa"
                    shininess: 14
                }
            ]
        }
        Entity {
            enabled: root.laneRibbonPoints(1).length > 1
            components: [
                LaneRibbonMesh { points: root.laneRibbonPoints(1); width: root.laneWidth(1) },
                PhongMaterial {
                    diffuse: root.laneColor(1)
                    ambient: root.laneColor(1)
                    specular: "#ffffff"
                    shininess: 18
                }
            ]
        }
        Entity {
            enabled: root.laneRibbonPoints(2).length > 1
            components: [
                LaneRibbonMesh { points: root.laneRibbonPoints(2); width: root.laneWidth(2) },
                PhongMaterial {
                    diffuse: root.laneColor(2)
                    ambient: root.laneColor(2)
                    specular: "#ffffff"
                    shininess: 18
                }
            ]
        }
        Entity {
            enabled: root.laneRibbonPoints(3).length > 1
            components: [
                LaneRibbonMesh { points: root.laneRibbonPoints(3); width: root.laneWidth(3) },
                PhongMaterial {
                    diffuse: root.laneColor(3)
                    ambient: root.laneColor(3)
                    specular: "#eef5fa"
                    shininess: 14
                }
            ]
        }

        // === EGO VEHICLE ===
        Entity {
            components: [
                SceneLoader { source: "qrc:/icons/test.obj" },
                Transform {
                    translation: Qt.vector3d(0, -0.85, root.egoVehicleZ)
                    scale3D: Qt.vector3d(0.032, 0.032, 0.032)
                    rotation: fromAxisAndAngle(Qt.vector3d(0, 1, 0), root.egoVehicleYaw())
                }
            ]
        }

        // === DETECTED OBJECTS ===
        Entity {
            enabled: root.objectAvailable(0)
            components: [ Transform { translation: Qt.vector3d(root.objectWorld(0).x, -0.85, root.objectWorld(0).z) } ]
            Entity { components: [ SceneLoader { source: "qrc:/icons/test.obj" }, Transform { scale3D: Qt.vector3d(root.objectWorldScale(0), root.objectWorldScale(0), root.objectWorldScale(0)); rotation: fromAxisAndAngle(Qt.vector3d(0,1,0), root.objectWorldYaw(0)) } ] }
        }
        Entity {
            enabled: root.objectAvailable(1)
            components: [ Transform { translation: Qt.vector3d(root.objectWorld(1).x, -0.85, root.objectWorld(1).z) } ]
            Entity { components: [ SceneLoader { source: "qrc:/icons/test.obj" }, Transform { scale3D: Qt.vector3d(root.objectWorldScale(1), root.objectWorldScale(1), root.objectWorldScale(1)); rotation: fromAxisAndAngle(Qt.vector3d(0,1,0), root.objectWorldYaw(1)) } ] }
        }
        Entity {
            enabled: root.objectAvailable(2)
            components: [ Transform { translation: Qt.vector3d(root.objectWorld(2).x, -0.85, root.objectWorld(2).z) } ]
            Entity { components: [ SceneLoader { source: "qrc:/icons/test.obj" }, Transform { scale3D: Qt.vector3d(root.objectWorldScale(2), root.objectWorldScale(2), root.objectWorldScale(2)); rotation: fromAxisAndAngle(Qt.vector3d(0,1,0), root.objectWorldYaw(2)) } ] }
        }
        Entity {
            enabled: root.objectAvailable(3)
            components: [ Transform { translation: Qt.vector3d(root.objectWorld(3).x, -0.85, root.objectWorld(3).z) } ]
            Entity { components: [ SceneLoader { source: "qrc:/icons/test.obj" }, Transform { scale3D: Qt.vector3d(root.objectWorldScale(3), root.objectWorldScale(3), root.objectWorldScale(3)); rotation: fromAxisAndAngle(Qt.vector3d(0,1,0), root.objectWorldYaw(3)) } ] }
        }
        Entity {
            enabled: root.objectAvailable(4)
            components: [ Transform { translation: Qt.vector3d(root.objectWorld(4).x, -0.85, root.objectWorld(4).z) } ]
            Entity { components: [ SceneLoader { source: "qrc:/icons/test.obj" }, Transform { scale3D: Qt.vector3d(root.objectWorldScale(4), root.objectWorldScale(4), root.objectWorldScale(4)); rotation: fromAxisAndAngle(Qt.vector3d(0,1,0), root.objectWorldYaw(4)) } ] }
        }
        Entity {
            enabled: root.objectAvailable(5)
            components: [ Transform { translation: Qt.vector3d(root.objectWorld(5).x, -0.85, root.objectWorld(5).z) } ]
            Entity { components: [ SceneLoader { source: "qrc:/icons/test.obj" }, Transform { scale3D: Qt.vector3d(root.objectWorldScale(5), root.objectWorldScale(5), root.objectWorldScale(5)); rotation: fromAxisAndAngle(Qt.vector3d(0,1,0), root.objectWorldYaw(5)) } ] }
        }
        Entity {
            enabled: root.objectAvailable(6)
            components: [ Transform { translation: Qt.vector3d(root.objectWorld(6).x, -0.85, root.objectWorld(6).z) } ]
            Entity { components: [ SceneLoader { source: "qrc:/icons/test.obj" }, Transform { scale3D: Qt.vector3d(root.objectWorldScale(6), root.objectWorldScale(6), root.objectWorldScale(6)); rotation: fromAxisAndAngle(Qt.vector3d(0,1,0), root.objectWorldYaw(6)) } ] }
        }
        Entity {
            enabled: root.objectAvailable(7)
            components: [ Transform { translation: Qt.vector3d(root.objectWorld(7).x, -0.85, root.objectWorld(7).z) } ]
            Entity { components: [ SceneLoader { source: "qrc:/icons/test.obj" }, Transform { scale3D: Qt.vector3d(root.objectWorldScale(7), root.objectWorldScale(7), root.objectWorldScale(7)); rotation: fromAxisAndAngle(Qt.vector3d(0,1,0), root.objectWorldYaw(7)) } ] }
        }
    }
}
