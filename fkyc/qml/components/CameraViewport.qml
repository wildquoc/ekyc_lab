import QtQuick
import QtQuick.Shapes
import Fkyc 1.0

Item {
    id: root
    property real unit: 1
    property Item blurSource: null
    clip: false

    readonly property real wellRadius: (bridge.screen === "loginResult" || bridge.screen === "citizenResult" || bridge.screen === "studentResult" || bridge.screen === "faceResult" ? Theme.radiusPhoto : 56) * root.unit
    readonly property bool captureHud: {
        var s = bridge.screen
        return s === "citizen" || s === "student"
    }
    readonly property bool faceHud: bridge.screen === "face" || bridge.screen === "login" || bridge.screen === "exam"
    readonly property bool resultHud: {
        var s = bridge.screen
        return s === "loginResult" || s === "citizenResult" || s === "studentResult" || s === "faceResult"
    }

    readonly property string titleMain: {
        if (bridge.screen === "citizen" || bridge.screen === "citizenResult")
            return "Show your"
        if (bridge.screen === "student" || bridge.screen === "studentResult")
            return "Show your"
        if (bridge.screen === "exam")
            return "Exam"
        if (bridge.screen === "login" || bridge.screen === "loginResult")
            return "Login"
        if (bridge.screen === "face" || bridge.screen === "faceResult")
            return "Register"
        return ""
    }
    readonly property string titleSub: {
        if (bridge.screen === "citizen" || bridge.screen === "citizenResult")
            return "Citizen Card"
        if (bridge.screen === "student" || bridge.screen === "studentResult")
            return "Student Card"
        if (bridge.screen === "exam")
            return "monitor"
        if (bridge.screen === "login" || bridge.screen === "loginResult")
            return "with FaceID"
        if (bridge.screen === "face" || bridge.screen === "faceResult")
            return "FaceID"
        return ""
    }
    readonly property string titleJoined: (titleMain + " " + titleSub).trim()
    readonly property string titleBlock: titleSub !== "" ? (titleMain + "\n" + titleSub) : titleMain

    readonly property string hintText: {
        if (bridge.errorText !== "")
            return bridge.errorText
        if (bridge.turnDirection === "left")
            return "Slowly turn your head to the Left."
        if (bridge.turnDirection === "right")
            return "Slowly turn your head to the Right."
        var prompt = bridge.prompt || ""
        if (prompt === "" || prompt === root.titleJoined)
            return ""
        return prompt
    }
    property color ringColor: {
        if (bridge.ovalColor === "green") return Theme.ok
        if (bridge.ovalColor === "yellow") return Theme.warn
        if (bridge.ovalColor === "red") return Theme.bad
        return "#3D9DFF"
    }

    Rectangle {
        anchors.fill: parent
        radius: root.wellRadius
        color: Theme.cameraWell
        antialiasing: true
    }

    Image {
        id: feed
        anchors.fill: parent
        fillMode: {
            if (bridge.screen === "loginResult" || bridge.screen === "citizenResult" || bridge.screen === "studentResult" || bridge.screen === "faceResult")
                return Image.PreserveAspectCrop
            return root.resultHud ? Image.PreserveAspectFit : Image.PreserveAspectCrop
        }
        cache: false
        asynchronous: false
        smooth: true
        source: {
            if (root.resultHud)
                return bridge.snapshotSeq > 0 ? ("image://camera/shot?" + bridge.snapshotSeq) : ""
            return bridge.frameSeq > 0 ? ("image://camera/live?" + bridge.frameSeq) : ""
        }
    }

    ShaderEffectSource {
        id: feedTex
        sourceItem: feed
        hideSource: roundFx.status === ShaderEffect.Compiled
        live: true
        smooth: true
    }

    ShaderEffect {
        id: roundFx
        anchors.fill: parent
        fragmentShader: Qt.resolvedUrl("../shaders/roundmask.frag.qsb")
        blending: true
        visible: status === ShaderEffect.Compiled && (root.resultHud ? bridge.snapshotSeq > 0 : bridge.frameSeq > 0)
        property var source: feedTex
        property vector2d size: Qt.vector2d(Math.max(1, root.width), Math.max(1, root.height))
        property real radius: root.wellRadius
    }

    Rectangle {
        visible: bridge.screen === "citizen"
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.72, parent.height * 1.2)
        height: width / 1.586
        radius: 16 * root.unit
        color: "transparent"
        border.width: 1.5
        border.color: Qt.rgba(1, 1, 1, 0.55)
    }

    Rectangle {
        visible: bridge.screen === "student"
        anchors.centerIn: parent
        width: parent.width * 0.72
        height: Math.max(88 * root.unit, parent.height * 0.28)
        radius: 12 * root.unit
        color: "transparent"
        border.width: 1.5
        border.color: Qt.rgba(1, 1, 1, 0.55)
    }

    Item {
        id: oval
        visible: root.faceHud
        width: Math.min(parent.width * 0.88, parent.height * 0.78)
        height: width * 1.22
        anchors.centerIn: parent
        onXChanged: root.publishOval()
        onYChanged: root.publishOval()
        onWidthChanged: {
            root.publishOval()
            ring.requestPaint()
        }
        onHeightChanged: {
            root.publishOval()
            ring.requestPaint()
        }
    }

    Shape {
        anchors.fill: oval
        visible: oval.visible
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 5
            strokeColor: root.ringColor
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg {
                path: {
                    var rx = Math.max(1, oval.width / 2 - 4)
                    var ry = Math.max(1, oval.height / 2 - 4)
                    var cx = oval.width / 2
                    var cy = oval.height / 2
                    return "M " + (cx - rx) + " " + cy
                        + " A " + rx + " " + ry + " 0 1 0 " + (cx + rx) + " " + cy
                        + " A " + rx + " " + ry + " 0 1 0 " + (cx - rx) + " " + cy
                }
            }
        }
    }

    Canvas {
        id: ring
        anchors.fill: oval
        visible: oval.visible && bridge.progress > 0.02
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (width < 8 || height < 8)
                return
            var rx = Math.max(1, (width - 10) / 2)
            var ry = Math.max(1, (height - 10) / 2)
            ctx.translate(width / 2, height / 2)
            ctx.scale(rx, ry)
            ctx.strokeStyle = "#ffffff"
            ctx.lineWidth = 4 / Math.max(rx, ry)
            ctx.lineCap = "round"
            ctx.beginPath()
            var start = -Math.PI / 2
            ctx.arc(0, 0, 1, start, start + Math.PI * 2 * bridge.progress)
            ctx.stroke()
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.captureHud || root.faceHud
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            bridge.tapFocus()
            focusMark.restart()
        }
    }

    Rectangle {
        id: focusMark
        width: 72 * root.unit
        height: 72 * root.unit
        anchors.centerIn: parent
        radius: 10 * root.unit
        color: "transparent"
        border.width: 2
        border.color: "#ffffff"
        opacity: 0
        visible: opacity > 0.02

        function restart() {
            fade.stop()
            opacity = 1
            fade.start()
        }

        SequentialAnimation {
            id: fade
            PauseAnimation { duration: 180 }
            NumberAnimation { target: focusMark; property: "opacity"; to: 0; duration: 420; easing.type: Easing.OutCubic }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.wellRadius
        color: "transparent"
        border.color: "#ffffff"
        border.width: 2
        antialiasing: true
    }

    Item {
        id: loginHint
        visible: root.faceHud && bridge.screen === "login" && root.hintText !== ""
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 18 * root.unit
        height: loginHintText.height + 16 * root.unit

        Rectangle {
            anchors.fill: parent
            radius: 14 * root.unit
            color: Qt.rgba(0, 0, 0, 0.55)
        }

        Text {
            id: loginHintText
            anchors.centerIn: parent
            width: parent.width - 24 * root.unit
            text: root.hintText
            color: "#ffffff"
            font.family: "SF Pro Display"
            font.pixelSize: 16 * root.unit
            wrapMode: Text.WordWrap
            maximumLineCount: 3
            horizontalAlignment: Text.AlignHCenter
        }
    }

    Item {
        id: hud
        visible: root.captureHud
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 36 * root.unit
        anchors.rightMargin: 36 * root.unit
        anchors.bottomMargin: 28 * root.unit
        height: Math.max(titleLabel.height, hintBox.height)

        Text {
            id: titleLabel
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: root.titleBlock
            color: "#ffffff"
            font.family: "SF Pro Display"
            font.pixelSize: 32 * root.unit
            font.weight: Font.Bold
            lineHeight: 1.08
            lineHeightMode: Text.ProportionalHeight
            style: Text.Raised
            styleColor: "#66000000"
        }

        Item {
            id: hintBox
            visible: root.hintText !== ""
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: hintCol.width + 28 * root.unit
            height: hintCol.height + 16 * root.unit

            Rectangle {
                anchors.fill: parent
                radius: 14 * root.unit
                color: Qt.rgba(0, 0, 0, 0.55)
            }

            Text {
                id: hintCol
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 14 * root.unit
                width: Math.min(implicitWidth, hud.width * 0.52)
                text: root.hintText
                color: "#ffffff"
                font.family: "SF Pro Display"
                font.pixelSize: 20 * root.unit
                font.weight: Font.Normal
                horizontalAlignment: Text.AlignRight
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
                maximumLineCount: 4
            }
        }
    }

    function publishOval() {
        if (!oval.visible)
            return
        var point = oval.mapToItem(null, 0, 0)
        bridge.setOval(point.x, point.y, oval.width, oval.height)
    }

    onXChanged: publishOval()
    onYChanged: publishOval()
    onWidthChanged: publishOval()
    onHeightChanged: publishOval()
    Connections {
        target: bridge
        function onNormChanged() { root.publishOval() }
        function onProgressChanged() { ring.requestPaint() }
        function onOvalColorChanged() { ring.requestPaint() }
    }
    Component.onCompleted: publishOval()
}
