import QtQuick
import Fkyc 1.0
import "../components"

Item {
    id: page
    property string notice: ""
    property real unit: 1
    property real ox: 0
    property real oy: 0
    property Item blurSource: null

    Image {
        x: page.ox + 346 * page.unit
        y: page.oy + 177 * page.unit
        width: 244 * page.unit
        height: 95 * page.unit
        source: logoSource
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
    }

    Item {
        x: page.ox + 244 * page.unit
        y: page.oy + 408 * page.unit
        width: 450 * page.unit
        height: 84 * page.unit
        Row {
            anchors.centerIn: parent
            spacing: 78 * page.unit
            Repeater {
                model: ["F", "K", "Y", "C"]
                Text {
                    required property string modelData
                    text: modelData
                    color: "#ffffff"
                    font.family: Theme.fontFamily
                    font.pixelSize: 78 * page.unit
                    font.weight: Font.Bold
                }
            }
        }
    }

    PillButton {
        x: page.ox + 292 * page.unit
        y: page.oy + 618 * page.unit
        width: 352 * page.unit
        height: 118 * page.unit
        frosted: true
        blurSource: page.blurSource
        label: "Log in"
        subtitle: "with FaceID"
        labelSize: 32 * page.unit
        subtitleSize: 26 * page.unit
        textFont: "SF Pro Display"
        iconSource: loginIcon
        onClicked: bridge.startLogin()
    }

    Item {
        x: page.ox + 267 * page.unit
        y: page.oy + 756 * page.unit
        width: 400 * page.unit
        height: 56 * page.unit
        Row {
            anchors.centerIn: parent
            spacing: 18 * page.unit
            Text {
                text: "or"
                color: "#ffffff"
                font.family: "SF Pro Display"
                font.pixelSize: 26 * page.unit
                font.weight: Font.Bold
                anchors.verticalCenter: parent.verticalCenter
            }
            PillButton {
                width: 280 * page.unit
                height: 56 * page.unit
                frosted: true
                blurSource: page.blurSource
                label: "Register"
                fadedSuffix: "FaceID"
                labelSize: 24 * page.unit
                textFont: "SF Pro Display"
                onClicked: bridge.startRegister()
            }
        }
    }

    Text {
        visible: page.notice !== ""
        x: page.ox + 267 * page.unit
        y: page.oy + 834 * page.unit
        width: 400 * page.unit
        horizontalAlignment: Text.AlignHCenter
        text: page.notice
        color: "#ffffff"
        font.family: Theme.fontFamily
        font.pixelSize: 16 * page.unit
        wrapMode: Text.WordWrap
    }

    GlassPanel {
        id: photoGlass
        x: page.ox + 773 * page.unit
        y: page.oy + 119 * page.unit
        width: 512 * page.unit
        height: 786 * page.unit
        glassRadius: 56 * page.unit
        blurSource: page.blurSource
        strength: 4
        fillOpacity: 0.24
        milk: 0.28
    }

    RoundPhoto {
        x: page.ox + 801 * page.unit
        y: page.oy + 147 * page.unit
        width: 456 * page.unit
        height: 245 * page.unit
        source: assetRoot + "/photos/green_campus_card.png"
    }
    RoundPhoto {
        x: page.ox + 801 * page.unit
        y: page.oy + 414 * page.unit
        width: 280 * page.unit
        height: 190 * page.unit
        source: assetRoot + "/photos/classroom_card.png"
    }
    RoundPhoto {
        x: page.ox + 881 * page.unit
        y: page.oy + 626 * page.unit
        width: 376 * page.unit
        height: 250 * page.unit
        source: assetRoot + "/photos/library_card.png"
    }
}
