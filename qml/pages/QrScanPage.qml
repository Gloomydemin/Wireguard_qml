import QtQuick 2.12
import QtQuick.Layouts 1.12
import QtMultimedia 5.12
import Lomiri.Components 1.3 as UITK
import io.thp.pyotherside 1.3

UITK.Page {
    id: qrPage
    signal qrDecoded(string text)

    property bool scanning: true
    property bool decoding: false
    property string capturePath: "/tmp/wg_qr_capture.jpg"

    header: UITK.PageHeader {
        title: i18n.tr("Scan QR code")
        trailingActionBar.actions: [
            UITK.Action {
                iconName: "close"
                onTriggered: {
                    scanning = false
                    captureTimer.stop()
                    camera.stop()
                    pageStack.pop()
                }
            }
        ]
    }

    Camera {
        id: camera
        captureMode: Camera.CaptureStillImage
        onCameraStatusChanged: {
            if (cameraStatus === Camera.ActiveStatus && !captureTimer.running) {
                captureTimer.start()
            }
        }
    }

    VideoOutput {
        anchors.fill: parent
        anchors.topMargin: header.height
        source: camera
        autoOrientation: true
        fillMode: VideoOutput.PreserveAspectCrop
        id: videoOutput
    }

    Rectangle {
        id: scanFrame
        width: parent.width * 0.62
        height: width
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        color: "transparent"
        border.width: units.gu(0.3)
        border.color: "white"
        radius: units.gu(1)
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: units.gu(3)
        spacing: units.gu(0.6)

        Text {
            id: statusText
            text: i18n.tr("Point the camera at the QR code")
            color: "white"
            font.pixelSize: units.gu(1.7)
            horizontalAlignment: Text.AlignHCenter
        }

        UITK.ActivityIndicator {
            running: decoding
            visible: decoding
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    Timer {
        id: captureTimer
        interval: 900
        repeat: true
        running: scanning && camera.cameraStatus === Camera.ActiveStatus && !decoding
        onTriggered: {
            if (!videoOutput.grabToImage) {
                return
            }
            decoding = true
            var tmpPath = "/tmp/wg_qr_frame_" + Date.now() + ".png"
            videoOutput.grabToImage(function(result) {
                if (!result || !result.saveToFile) {
                    decoding = false
                    return
                }
                result.saveToFile(tmpPath)
                decodeImage(tmpPath)
            })
        }
    }

    function decodeImage(path) {
        var cleanPath = path
        if (cleanPath.startsWith("file://")) {
            cleanPath = cleanPath.substring(7)
        }
        python.call('vpn.instance.decode_qr_image', [cleanPath], function(result) {
            if (result.error) {
                if (result.error === "NO_QR") {
                    decoding = false
                    return
                }
                decoding = false
                statusText.text = i18n.tr("Could not decode QR")
                toast.show(i18n.tr("QR error: ") + result.error)
                return
            }
            decoding = false
            scanning = false
            captureTimer.stop()
            camera.stop()
            qrPage.qrDecoded(result.text)
            pageStack.pop()
        })
    }

    Component.onCompleted: {
        camera.start()
    }

    Component.onDestruction: {
        scanning = false
        captureTimer.stop()
        camera.stop()
    }
}
