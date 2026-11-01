import QtQuick
import Fkyc 1.0

Item {
    id: root
    property Item blurSource: null
    property real glassRadius: Theme.radiusGlass
    property real strength: 7
    property real fillOpacity: 0.16
    property real milk: 0
    readonly property real pad: 36

    Rectangle {
        anchors.fill: parent
        anchors.margins: 2
        radius: root.glassRadius
        color: Qt.rgba(1, 1, 1, root.fillOpacity)
        border.width: 0
        visible: fx.status !== ShaderEffect.Compiled
        antialiasing: true
    }

    ShaderEffectSource {
        id: grab
        visible: false
        live: false
        hideSource: false
        smooth: true
        mipmap: true
        sourceItem: root.blurSource
        sourceRect: root.sampleRect()
        textureSize: Qt.size(Math.max(2, Math.round(root.width + root.pad * 2)),
                             Math.max(2, Math.round(root.height + root.pad * 2)))
    }

    ShaderEffect {
        id: fx
        anchors.fill: parent
        fragmentShader: Qt.resolvedUrl("../shaders/glass.frag.qsb")
        blending: true
        antialiasing: true
        property var source: grab
        property vector2d size: Qt.vector2d(Math.max(1, root.width), Math.max(1, root.height))
        property vector2d texSize: Qt.vector2d(root.width + root.pad * 2, root.height + root.pad * 2)
        property real radius: root.glassRadius
        property real pad: root.pad
        property real strength: root.strength
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 2
        radius: root.glassRadius
        color: Qt.rgba(1, 1, 1, root.milk)
        border.width: 0
        visible: root.milk > 0.001
        antialiasing: true
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 2
        radius: root.glassRadius
        color: "transparent"
        antialiasing: true
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.06) }
            GradientStop { position: 0.18; color: Qt.rgba(1, 1, 1, 0.02) }
            GradientStop { position: 0.55; color: "#00000000" }
            GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0.05) }
        }
    }

    Canvas {
        id: rim
        anchors.fill: parent
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (width < 16 || height < 16)
                return

            var r = Math.min(root.glassRadius, width / 2, height / 2)
            var inset = 3.0
            var rad = Math.max(2, r - inset)
            var top = "rgba(255, 255, 255, "

            ctx.lineCap = "round"
            ctx.lineJoin = "round"

            ctx.lineWidth = Math.max(1.15, r * 0.028)
            var g1 = ctx.createLinearGradient(width * 0.22, inset, width - inset, r * 1.15)
            g1.addColorStop(0.00, top + "0)")
            g1.addColorStop(0.18, top + "0.42)")
            g1.addColorStop(0.52, top + "0.78)")
            g1.addColorStop(0.80, top + "0.32)")
            g1.addColorStop(1.00, top + "0)")
            ctx.strokeStyle = g1
            ctx.beginPath()
            ctx.moveTo(width * 0.24, inset)
            ctx.lineTo(width - r, inset)
            ctx.arc(width - r, r, rad, -Math.PI / 2, 0.18, false)
            ctx.stroke()

            ctx.lineWidth = Math.max(1.05, r * 0.024)
            var g2 = ctx.createLinearGradient(width * 0.78, height - inset, inset, height - r * 1.15)
            g2.addColorStop(0.00, top + "0)")
            g2.addColorStop(0.20, top + "0.18)")
            g2.addColorStop(0.50, top + "0.36)")
            g2.addColorStop(0.80, top + "0.14)")
            g2.addColorStop(1.00, top + "0)")
            ctx.strokeStyle = g2
            ctx.beginPath()
            ctx.moveTo(width * 0.76, height - inset)
            ctx.lineTo(r, height - inset)
            ctx.arc(r, height - r, rad, Math.PI / 2, Math.PI + 0.08, false)
            ctx.stroke()
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    function sampleRect() {
        if (!root.blurSource || root.width < 2 || root.height < 2)
            return Qt.rect(0, 0, 2, 2)
        var origin = root.mapToItem(root.blurSource, -root.pad, -root.pad)
        return Qt.rect(origin.x, origin.y, root.width + root.pad * 2, root.height + root.pad * 2)
    }

    function refresh() {
        grab.sourceRect = root.sampleRect()
        grab.scheduleUpdate()
        rim.requestPaint()
    }

    onXChanged: refresh()
    onYChanged: refresh()
    onWidthChanged: refresh()
    onHeightChanged: refresh()
    onGlassRadiusChanged: refresh()
    Component.onCompleted: refresh()

    Timer {
        interval: 80
        repeat: true
        running: ticks < 8
        property int ticks: 0
        onTriggered: {
            root.refresh()
            ticks += 1
        }
    }
}
