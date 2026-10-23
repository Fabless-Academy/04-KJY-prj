#include "laneribbonmesh.h"

#include <QByteArray>
#include <QVector3D>
#include <QtMath>

namespace {
struct RibbonPoint {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

RibbonPoint parsePoint(const QVariant &value) {
    // QML의 {x,y,z} map을 C++ 계산용 struct로 변환
    const QVariantMap map = value.toMap();
    RibbonPoint point;
    point.x = map.value(QStringLiteral("x")).toFloat();
    point.y = map.value(QStringLiteral("y")).toFloat();
    point.z = map.value(QStringLiteral("z")).toFloat();
    return point;
}

void appendVertex(QByteArray &bytes, const RibbonPoint &point, const QVector3D &normal) {
    // position과 normal을 한 vertex 레코드로 interleaved 저장
    const float values[] = {point.x, point.y, point.z, normal.x(), normal.y(), normal.z()};
    bytes.append(reinterpret_cast<const char *>(values), sizeof(values));
}
} // namespace

LaneRibbonMesh::LaneRibbonMesh(Qt3DCore::QNode *parent)
    : Qt3DRender::QGeometryRenderer(parent),
      geometry_(new Qt3DRender::QGeometry(this)),
      vertexBuffer_(new Qt3DRender::QBuffer(Qt3DRender::QBuffer::VertexBuffer, geometry_)),
      positionAttribute_(new Qt3DRender::QAttribute(geometry_)),
      normalAttribute_(new Qt3DRender::QAttribute(geometry_)) {
    // 리본은 index buffer 없이 triangle 목록으로 직접 그림
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

QVariantList LaneRibbonMesh::points() const {
    return points_;
}

void LaneRibbonMesh::setPoints(const QVariantList &points) {
    if (points_ == points)
        return;
    points_ = points;
    updateGeometry();
    emit pointsChanged();
}

float LaneRibbonMesh::width() const {
    return width_;
}

void LaneRibbonMesh::setWidth(float width) {
    if (qFuzzyCompare(width_, width))
        return;
    width_ = width;
    updateGeometry();
    emit widthChanged();
}

void LaneRibbonMesh::updateGeometry() {
    if (points_.size() < 2 || width_ <= 0.0f) {
        vertexBuffer_->setData(QByteArray());
        positionAttribute_->setCount(0);
        normalAttribute_->setCount(0);
        setVertexCount(0);
        return;
    }

    QByteArray bytes;
    bytes.reserve((points_.size() - 1) * 12 * 6 * sizeof(float));
    const QVector3D normal(0.0f, 1.0f, 0.0f);
    const float halfWidth = width_ * 0.5f;
    int vertexCount = 0;

    for (int i = 0; i < points_.size() - 1; ++i) {
        // 인접한 두 점 사이에 좌/우 오프셋을 만들어 사각형 한 구간을 생성
        const RibbonPoint p0 = parsePoint(points_.at(i));
        const RibbonPoint p1 = parsePoint(points_.at(i + 1));
        const float dx = p1.x - p0.x;
        const float dz = p1.z - p0.z;
        const float length = qSqrt(dx * dx + dz * dz);
        if (length < 1e-4f)
            continue;

        const float nx = -dz / length * halfWidth;
        const float nz = dx / length * halfWidth;

        RibbonPoint left0;
        left0.x = p0.x + nx;
        left0.y = p0.y;
        left0.z = p0.z + nz;
        RibbonPoint right0;
        right0.x = p0.x - nx;
        right0.y = p0.y;
        right0.z = p0.z - nz;
        RibbonPoint left1;
        left1.x = p1.x + nx;
        left1.y = p1.y;
        left1.z = p1.z + nz;
        RibbonPoint right1;
        right1.x = p1.x - nx;
        right1.y = p1.y;
        right1.z = p1.z - nz;

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

    // 완성된 vertex buffer를 geometry attribute에 반영
    vertexBuffer_->setData(bytes);
    positionAttribute_->setCount(vertexCount);
    normalAttribute_->setCount(vertexCount);
    setVertexCount(vertexCount);
}
