import QtQuick
import QtQuick.Effects

Item {
    Image {
        id: photo
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        source: assetRoot + "/bg/campus_blur.png"
        asynchronous: false
        smooth: true
        mipmap: true
    }

    MultiEffect {
        anchors.fill: parent
        source: photo
        blurEnabled: true
        blur: 0.7
        blurMax: 48
        brightness: -0.14
        contrast: 0.06
    }

    Rectangle {
        anchors.fill: parent
        color: "#2a000000"
    }
}
