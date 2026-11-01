import QtQuick
import QtQuick.Effects
import Fkyc 1.0

Item {
    id: root
    property string label: ""
    property string subtitle: ""
    property string fadedSuffix: ""
    property string iconSource: ""
    property bool pulse: false
    property bool frosted: false
    property real frostFill: 0.16
    property Item blurSource: null
    property color labelColor: frosted ? "#ffffff" : Theme.inkOnLight
    property real labelSize: 0
    property real subtitleSize: 0
    property string textFont: ""
    signal clicked()

    implicitHeight: label.indexOf("\n") >= 0 ? 78 : 56
    implicitWidth: 168

    readonly property real textBlock: {
        var h = root.labelSize > 0 ? root.labelSize : Theme.fontButton
        if (root.subtitle !== "")
            h += 4 + (root.labelSize > 0 ? root.labelSize : (root.subtitleSize > 0 ? root.subtitleSize : Theme.fontButton))
        return h
    }
    readonly property real discSize: root.iconSource !== "" ? Math.min(root.height * 0.78, root.textBlock * 1.32) : 0
    readonly property real discPad: (root.height - root.discSize) / 2
    HoverHandler {
        id: hover
    }
    readonly property bool hovered: hover.hovered || mouse.containsMouse
    readonly property bool hot: root.hovered || mouse.pressed
    property bool breath: false
    property real glowLevel: mouse.pressed ? 0.88 : root.hovered ? 0.68 : (pulse && breath ? 0.52 : pulse ? 0.28 : 0)
    property real haloSpread: mouse.pressed ? 20 : root.hovered ? 18 : (pulse ? 14 : 10)
    property real coreSpread: mouse.pressed ? 5 : 3

    Timer {
        interval: 900
        repeat: true
        running: root.pulse && !root.hot
        onTriggered: root.breath = !root.breath
    }

    Rectangle {
        id: halo
        anchors.fill: parent
        anchors.margins: -root.haloSpread
        radius: height / 2
        color: "#ff9a1f"
        opacity: root.glowLevel * 0.52
        layer.enabled: opacity > 0.02
        layer.effect: MultiEffect {
            blurEnabled: true
            blur: 1
            blurMax: 56
        }
        Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
        Behavior on anchors.margins { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    }

    Rectangle {
        id: core
        anchors.fill: parent
        anchors.margins: -root.coreSpread
        radius: height / 2
        color: "#ffc14d"
        opacity: root.glowLevel * 0.70
        layer.enabled: opacity > 0.02
        layer.effect: MultiEffect {
            blurEnabled: true
            blur: 0.9
            blurMax: 28
        }
        Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
        Behavior on anchors.margins { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    }

    Rectangle {
        id: glass
        anchors.fill: parent
        radius: height / 2
        color: root.frosted
               ? (mouse.pressed ? Qt.rgba(1, 0.78, 0.32, Math.max(0.28, root.frostFill + 0.12))
                                : root.hovered ? Qt.rgba(1, 0.82, 0.38, Math.max(0.20, root.frostFill + 0.06))
                                : Qt.rgba(1, 1, 1, root.frostFill))
               : Theme.pill
        border.width: 0
        Behavior on color { ColorAnimation { duration: 180; easing.type: Easing.OutCubic } }
    }

    Canvas {
        id: rim
        anchors.fill: parent
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (width < 8 || height < 8)
                return
            var r = height / 2
            var inset = 1.15
            var cxR = width - r
            var cxL = r
            var cy = r
            var rad = r - inset
            var hot = root.hot
            var top = hot ? "rgba(255, 196, 80, " : "rgba(255, 255, 255, "
            var bot = hot ? "rgba(255, 196, 80, " : "rgba(255, 255, 255, "

            ctx.lineCap = "round"
            ctx.lineJoin = "round"

            ctx.lineWidth = Math.max(1.1, height * 0.013)
            var g1 = ctx.createLinearGradient(width * 0.28, inset, width - inset, height * 0.46)
            g1.addColorStop(0.00, top + "0)")
            g1.addColorStop(0.18, top + "0.55)")
            g1.addColorStop(0.48, top + "0.82)")
            g1.addColorStop(0.78, top + "0.38)")
            g1.addColorStop(1.00, top + "0)")
            ctx.strokeStyle = g1
            ctx.beginPath()
            ctx.moveTo(width * 0.30, inset)
            ctx.lineTo(cxR, inset)
            ctx.arc(cxR, cy, rad, -Math.PI / 2, 0.22, false)
            ctx.stroke()

            ctx.lineWidth = Math.max(1.0, height * 0.011)
            var g2 = ctx.createLinearGradient(width * 0.72, height - inset, inset, height * 0.54)
            g2.addColorStop(0.00, bot + "0)")
            g2.addColorStop(0.20, bot + "0.22)")
            g2.addColorStop(0.50, bot + "0.40)")
            g2.addColorStop(0.80, bot + "0.16)")
            g2.addColorStop(1.00, bot + "0)")
            ctx.strokeStyle = g2
            ctx.beginPath()
            ctx.moveTo(width * 0.70, height - inset)
            ctx.lineTo(cxL, height - inset)
            ctx.arc(cxL, cy, rad, Math.PI / 2, Math.PI + 0.08, false)
            ctx.stroke()
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    Connections {
        target: root
        function onHotChanged() { rim.requestPaint() }
    }

    Rectangle {
        id: iconDisc
        visible: root.iconSource !== ""
        x: root.discPad
        anchors.verticalCenter: parent.verticalCenter
        width: root.discSize
        height: width
        radius: width / 2
        color: Qt.rgba(1, 1, 1, 0.42)

        Image {
            anchors.centerIn: parent
            anchors.horizontalCenterOffset: -parent.width * 0.05
            source: root.iconSource
            width: parent.width * 0.52
            height: width
            fillMode: Image.PreserveAspectFit
            horizontalAlignment: Image.AlignHCenter
            verticalAlignment: Image.AlignVCenter
            smooth: true
            mipmap: true
        }
    }

    Column {
        id: copy
        x: root.iconSource !== "" ? root.discPad + root.discSize + root.discPad * 1.2 : (root.width - width) / 2
        spacing: -Math.max(4, root.labelSize * 0.2)
        anchors.verticalCenter: parent.verticalCenter

        Row {
            spacing: root.labelSize * 0.18
            Text {
                text: root.label
                color: root.labelColor
                font.family: root.textFont !== "" ? root.textFont : Theme.fontFamily
                font.pixelSize: root.labelSize > 0 ? root.labelSize : Theme.fontButton
                font.weight: Font.Bold
            }
            Text {
                visible: root.fadedSuffix !== ""
                text: root.fadedSuffix
                color: "#ffffff"
                opacity: 0.5
                font.family: root.textFont !== "" ? root.textFont : Theme.fontFamily
                font.pixelSize: root.labelSize > 0 ? root.labelSize : Theme.fontButton
                font.weight: Font.Bold
            }
        }

        Text {
            visible: root.subtitle !== ""
            text: root.subtitle
            color: "#ffffff"
            opacity: 0.5
            font.family: root.textFont !== "" ? root.textFont : Theme.fontFamily
            font.pixelSize: root.labelSize > 0 ? root.labelSize : (root.subtitleSize > 0 ? root.subtitleSize : Theme.fontButton)
            font.weight: Font.Bold
        }
    }

    scale: mouse.pressed ? 0.975 : root.hovered ? 1.015 : 1
    transformOrigin: Item.Center
    Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

}
