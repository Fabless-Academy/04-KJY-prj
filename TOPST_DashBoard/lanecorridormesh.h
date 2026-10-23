#ifndef LANECORRIDORMESH_H
#define LANECORRIDORMESH_H

#include <QVariantList>

#include <Qt3DRender/QAttribute>
#include <Qt3DRender/QBuffer>
#include <Qt3DRender/QGeometry>
#include <Qt3DRender/QGeometryRenderer>

class LaneCorridorMesh : public Qt3DRender::QGeometryRenderer {
    Q_OBJECT
    // left/right 경계 점 목록을 받아 두 선 사이를 면으로 채움
    Q_PROPERTY(QVariantList leftPoints READ leftPoints WRITE setLeftPoints NOTIFY leftPointsChanged)
    Q_PROPERTY(QVariantList rightPoints READ rightPoints WRITE setRightPoints NOTIFY rightPointsChanged)

public:
    explicit LaneCorridorMesh(Qt3DCore::QNode *parent = nullptr);

    QVariantList leftPoints() const;
    void setLeftPoints(const QVariantList &points);

    QVariantList rightPoints() const;
    void setRightPoints(const QVariantList &points);

signals:
    void leftPointsChanged();
    void rightPointsChanged();

private:
    // 좌우 경계 점 쌍을 triangle 목록으로 펼쳐 corridor mesh를 만듦
    void updateGeometry();

    QVariantList leftPoints_;
    QVariantList rightPoints_;
    Qt3DRender::QGeometry *geometry_ = nullptr;
    Qt3DRender::QBuffer *vertexBuffer_ = nullptr;
    Qt3DRender::QAttribute *positionAttribute_ = nullptr;
    Qt3DRender::QAttribute *normalAttribute_ = nullptr;
};

#endif
