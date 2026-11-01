import QtQuick
import QtQuick.Layouts

RowLayout {
    signal confirm()
    signal redo()
    spacing: 16
    PillButton {
        label: "Confirm"
        enabled: !bridge.busy
        opacity: enabled ? 1 : 0.45
        onClicked: if (enabled) confirm()
    }
    PillButton {
        label: "Redo"
        onClicked: redo()
    }
}
