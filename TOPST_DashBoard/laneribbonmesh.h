#ifndef LANERIBBONMESH_H
#define LANERIBBONMESH_H

#include <QVariantList>

#include <Qt3DRender/QAttribute>
#include <Qt3DRender/QBuffer>
#include <Qt3DRender/QGeometry>
#include <Qt3DRender/QGeometryRenderer>

class LaneRibbonMesh : public Qt3DRender::QGeometryRenderer {
    Q_OBJECT
    // points는 월드 좌표 목록, width는 그 점들을 따라 만드는 리본의 폭
    Q_PROPERTY(QVariantList points READ points WRITE setPoints NOTIFY pointsChanged)
    Q_PROPERTY(float width READ width WRITE setWidth NOTIFY widthChanged)

public:
    explicit LaneRibbonMesh(Qt3DCore::QNode *parent = nullptr);

    QVariantList points() const;
    void setPoints(const QVariantList &points);

    float width() const;
    void setWidth(float width);

signals:
    void pointsChanged();
    void widthChanged();

private:
    // 입력 점이 바뀔 때마다 triangle 기반 geometry를 다시 구성
    void updateGeometry();

    QVariantList points_;
    float width_ = 0.2f;
    Qt3DRender::QGeometry *geometry_ = nullptr;
    Qt3DRender::QBuffer *vertexBuffer_ = nullptr;
    Qt3DRender::QAttribute *positionAttribute_ = nullptr;
    Qt3DRender::QAttribute *normalAttribute_ = nullptr;
};

#endif
