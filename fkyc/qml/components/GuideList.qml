import QtQuick
import Fkyc 1.0

Item {
    id: root
    property real unit: 1
    implicitWidth: 250 * unit
    implicitHeight: card.height

    Rectangle {
        id: card
        width: parent.width
        height: col.height + 36 * root.unit
        radius: 36 * root.unit
        color: Qt.rgba(1, 1, 1, 0.88)

        Column {
            id: col
            x: 22 * root.unit
            y: 20 * root.unit
            width: parent.width - 44 * root.unit
            spacing: 14 * root.unit

            Text {
                text: "Steps"
                color: Theme.inkOnLight
                font.family: Theme.fontFamily
                font.pixelSize: 22 * root.unit
                font.weight: Font.Bold
            }

            Repeater {
                model: bridge.guides
                delegate: Item {
                    required property var modelData
                    required property int index
                    width: col.width
                    height: 44 * root.unit

                    Rectangle {
                        visible: index < bridge.guides.length - 1
                        x: 13 * root.unit - 1
                        y: 30 * root.unit
                        width: 2
                        height: 28 * root.unit
                        color: Theme.processLine
                    }

                    Rectangle {
                        id: badge
                        width: 26 * root.unit
                        height: width
                        radius: width / 2
                        color: modelData.state === "current" ? Theme.processCurrent
                             : modelData.state === "done" ? Theme.ok
                             : Theme.processIdle

                        Text {
                            anchors.centerIn: parent
                            text: String(modelData.index || (index + 1))
                            color: modelData.state === "todo" ? Theme.inkOnLight : "#ffffff"
                            font.family: Theme.fontFamily
                            font.pixelSize: 13 * root.unit
                            font.weight: Font.Bold
                        }
                    }

                    Column {
                        anchors.verticalCenter: badge.verticalCenter
                        x: 36 * root.unit
                        width: parent.width - 40 * root.unit
                        spacing: 1

                        Text {
                            text: modelData.title || ""
                            color: modelData.state === "current" ? Theme.processCurrent : Theme.inkOnLight
                            font.family: Theme.fontFamily
                            font.pixelSize: 15 * root.unit
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                            width: parent.width
                        }
                        Text {
                            text: modelData.caption || ""
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: 11 * root.unit
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }
                }
            }
        }
    }
}
