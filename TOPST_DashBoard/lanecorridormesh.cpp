#include "lanecorridormesh.h"

#include <QByteArray>
#include <QVector3D>

namespace {
struct CorridorPoint {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

CorridorPoint parsePoint(const QVariant &value) {
    // QML point map을 corridor 계산용 struct로 변환
    const QVariantMap map = value.toMap();
    CorridorPoint point;
    point.x = map.value(QStringLiteral("x")).toFloat();
    point.y = map.value(QStringLiteral("y")).toFloat();
    point.z = map.value(QStringLiteral("z")).toFloat();
    return point;
}

void appendVertex(QByteArray &bytes, const CorridorPoint &point, const QVector3D &normal) {
    const float values[] = {point.x, point.y, point.z, normal.x(), normal.y(), normal.z()};
    bytes.append(reinterpret_cast<const char *>(values), sizeof(values));
}
} // namespace

LaneCorridorMesh::LaneCorridorMesh(Qt3DCore::QNode *parent)
    : Qt3DRender::QGeometryRenderer(parent),
      geometry_(new Qt3DRender::QGeometry(this)),
      vertexBuffer_(new Qt3DRender::QBuffer(Qt3DRender::QBuffer::VertexBuffer, geometry_)),
      positionAttribute_(new Qt3DRender::QAttribute(geometry_)),
      normalAttribute_(new Qt3DRender::QAttribute(geometry_)) {
    // corridor는 좌우 차선 사이를 triangle 목록으로 직접 채워 그림
    setPrimitiveType(Qt3DRender::QGeometryRenderer::Triangles);
    setGeometry(geometry_);

    positionAttribute_->setName(Qt3DRender::QAttribute::defaultPositionAttributeName());
    positionAttribute_->setAttributeType(Qt3DRender::QAttribute::VertexAttribute);
    positionAttribute_->setVertexBaseType(Qt3DRender::QAttribute::Float);
    positionAttribute_->setVertexSize(3);
    positionAttribute_->setBuffer(vertexBuffer_);
    positionAttribute_->setByteStride(6 * sizeof(float));
    positionAttribute_->setByteOffset(0);

    normalAttribute_->setName(Qt3DRender::QAttribute::defaultNormalAttributeName());
    normalAttribute_->setAttributeType(Qt3DRender::QAttribute::VertexAttribute);
    normalAttribute_->setVertexBaseType(Qt3DRender::QAttribute::Float);
    normalAttribute_->setVertexSize(3);
    normalAttribute_->setBuffer(vertexBuffer_);
    normalAttribute_->setByteStride(6 * sizeof(float));
    normalAttribute_->setByteOffset(3 * sizeof(float));

    geometry_->addAttribute(positionAttribute_);
    geometry_->addAttribute(normalAttribute_);
    geometry_->setBoundingVolumePositionAttribute(positionAttribute_);
    updateGeometry();
}

QVariantList LaneCorridorMesh::leftPoints() const {
    return leftPoints_;
}

void LaneCorridorMesh::setLeftPoints(const QVariantList &points) {
    if (leftPoints_ == points)
        return;
    leftPoints_ = points;
    updateGeometry();
    emit leftPointsChanged();
}

QVariantList LaneCorridorMesh::rightPoints() const {
    return rightPoints_;
}

void LaneCorridorMesh::setRightPoints(const QVariantList &points) {
    if (rightPoints_ == points)
        return;
    rightPoints_ = points;
    updateGeometry();
    emit rightPointsChanged();
}

void LaneCorridorMesh::updateGeometry() {
    const int count = qMin(leftPoints_.size(), rightPoints_.size());
    if (count < 2) {
        vertexBuffer_->setData(QByteArray());
        positionAttribute_->setCount(0);
        normalAttribute_->setCount(0);
        setVertexCount(0);
        return;
    }

    QByteArray bytes;
    bytes.reserve((count - 1) * 12 * 6 * sizeof(float));
    const QVector3D normal(0.0f, 1.0f, 0.0f);
    int vertexCount = 0;

    for (int i = 0; i < count - 1; ++i) {
        // 같은 인덱스의 좌/우 경계 점 4개로 한 구간의 사각형 면을 만듦
        const CorridorPoint left0 = parsePoint(leftPoints_.at(i));
        const CorridorPoint right0 = parsePoint(rightPoints_.at(i));
        const CorridorPoint left1 = parsePoint(leftPoints_.at(i + 1));
        const CorridorPoint right1 = parsePoint(rightPoints_.at(i + 1));

        appendVertex(bytes, left0, normal);
        appendVertex(bytes, right0, normal);
        appendVertex(bytes, left1, normal);
        appendVertex(bytes, right0, normal);
        appendVertex(bytes, right1, normal);
        appendVertex(bytes, left1, normal);

        appendVertex(bytes, left1, normal);
        appendVertex(bytes, right0, normal);
        appendVertex(bytes, left0, normal);
        appendVertex(bytes, left1, normal);
        appendVertex(bytes, right1, normal);
        appendVertex(bytes, right0, normal);
        vertexCount += 12;
    }

    // 새 corridor vertex buffer를 Qt3D geometry에 반영
    vertexBuffer_->setData(bytes);
    positionAttribute_->setCount(vertexCount);
    normalAttribute_->setCount(vertexCount);
    setVertexCount(vertexCount);
}
