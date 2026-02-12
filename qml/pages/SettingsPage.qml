import QtQuick 2.0
import QtQuick.Layouts 1.12
import Lomiri.Components 1.3 as UITK
import Lomiri.Components.Popups 1.3 as Popups
import io.thp.pyotherside 1.3
import Qt.labs.settings 1.0

import "../components"

UITK.Page {
    id: settingsPage

    Settings {
        id: settings
        property bool finishedWizard: false
        property bool useUserspace: true
        property bool canUseKmod: false
        property bool allowExternalControl: false
    }

    property string versionLabel: "WireGuard for Ubuntu Touch"
    property string backendLabel: ""

    Toast { id: toast }

    header: UITK.PageHeader {
        id: header
        title: i18n.tr("Settings")

        leadingActionBar.actions: [
            UITK.Action {
                iconName: "back"
                onTriggered: {
                    stack.clear()
                    stack.push(Qt.resolvedUrl("PickProfilePage.qml"))
                }
            }
        ]
    }

    Flickable {
        id: flick
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        property int pad: units.gu(2)
        contentWidth: flick.width
        contentHeight: contentCol.implicitHeight + pad * 2
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        Column {
            id: contentCol
            x: flick.pad
            y: flick.pad
            width: flick.width - flick.pad * 2
            spacing: units.gu(2)
            clip: false

            Rectangle {
                width: contentCol.width
                color: "#1f1f1f"
                radius: units.gu(1)
                border.color: "#2b2b2b"
                border.width: 1
                property int pad: units.gu(2.4)
                height: Math.max(cardRow.implicitHeight + pad * 2, units.gu(7))
                Row {
                    id: cardRow
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: parent.pad
                    anchors.rightMargin: parent.pad
                    spacing: units.gu(1.2)

                    Image {
                        source: Qt.resolvedUrl("../../assets/logo.png")
                        width: units.gu(5)
                        height: width
                        fillMode: Image.PreserveAspectFit
                    }
                    Column {
                        spacing: units.gu(0.4)
                        width: contentCol.width - units.gu(9)
                        UITK.Label {
                            id: titleLbl
                            text: versionLabel
                            color: "white"
                            font.pixelSize: units.gu(2.0)
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }
                        UITK.Label {
                            id: backendLbl
                            text: backendLabel
                            color: "#cccccc"
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            SettingsItem {
                title: i18n.tr("Export tunnels to zip file")
                description: i18n.tr("Zip file will be saved to Downloads")
                onClicked: {
                    python.call('vpn.instance.export_confs_zip', [], function(res) {
                        if (res.error) {
                            toast.show(i18n.tr("Export error: ") + res.error)
                        } else {
                            if (res.warning) {
                                toast.show(i18n.tr("Saved: ") + res.path + " (" + res.warning + ")")
                            } else {
                                toast.show(i18n.tr("Saved: ") + res.path)
                            }
                        }
                    })
                }
            }

            SettingsItem {
                title: i18n.tr("View application logs")
                description: i18n.tr("Logs may help with debugging")
                onClicked: Qt.openUrlExternally("file:///home/phablet/.cache/wireguard.sysadmin/")
            }

            SettingsItem {
                title: i18n.tr("Use userspace implementation")
                description: i18n.tr("May be slower and less stable")
                control: UITK.Switch {
                    enabled: settings.canUseKmod
                    checked: settings.useUserspace
                    onCheckedChanged: {
                        settings.useUserspace = checked
                        if (typeof root !== "undefined" && root.settings) {
                            root.settings.useUserspace = checked
                        }
                    }
                }
            }

            SettingsItem {
                title: i18n.tr("Re-check kernel module")
                description: i18n.tr("Run kernel and sudo check wizard")
                onClicked: {
                    stack.clear()
                    stack.push(Qt.resolvedUrl("WizardPage.qml"))
                }
            }

            SettingsItem {
                title: i18n.tr("Bug report")
                description: i18n.tr("Report a problem on GitHub")
                onClicked: Qt.openUrlExternally("https://github.com/Gloomydemin/Wireguard_qml/issues/new/choose")
            }

            Column {
                width: contentCol.width
                spacing: units.gu(1)
                UITK.Label {
                    text: i18n.tr("⭐ Support the project")
                    color: "#cccccc"
                    font.bold: true
                }
                UITK.Button {
                    text: i18n.tr("Support Wireguard_qml development")
                    iconName: "star"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    onClicked: Qt.openUrlExternally("https://yoomoney.ru/to/4100119470150396")
                }
            }

            Rectangle { height: units.gu(2); width: 1; color: "transparent" }
        }
    }

    Python {
        id: python
        Component.onCompleted: {
            addImportPath(Qt.resolvedUrl('../../src/'))
            importModule('vpn', function () {
                if (typeof root !== "undefined" && root.pwd !== undefined) {
                    python.call('vpn.instance.set_pwd', [root.pwd], function(result){});
                }
                python.call('vpn.instance.get_wireguard_version', [], function(res) {
                    var ver = res && res.version ? res.version : ""
                    versionLabel = "WireGuard for Ubuntu Touch "
                    backendLabel = res && res.backend ? res.backend : ""
                })
            })
        }
    }
}
