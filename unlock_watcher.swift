#!/usr/bin/env swift
/**
 * Screen Unlock Watcher for macOS
 *
 * This helper listens for screen unlock events (including Touch ID)
 * and triggers the inspirational quotes app.
 * Also includes a menu bar indicator for the 20-20-20 eye break timer.
 *
 * Compile with: swiftc -o unlock_watcher unlock_watcher.swift
 */

import Foundation
import Cocoa

// Timestamp formatter
func timestamp() -> String {
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
    return formatter.string(from: Date())
}

func log(_ message: String) {
    print("[\(timestamp())] \(message)")
    fflush(stdout)  // Ensure immediate output
}

class ScreenUnlockWatcher: NSObject, NSMenuDelegate {
    let scriptPath: String
    var lastTriggerTime: Date = Date.distantPast
    var lastEyeBreakTriggerTime: Date = Date.distantPast
    let cooldownSeconds: TimeInterval = 60  // Prevent multiple triggers within 60 seconds
    let eyeBreakIntervalSeconds: TimeInterval = 20 * 60  // 20 minutes
    var eyeBreakTimer: Timer?

    // Menu bar components
    var statusItem: NSStatusItem!
    var countdownMenuItem: NSMenuItem!
    var pauseMenuItem: NSMenuItem!
    var menuUpdateTimer: Timer?  // Timer for updating menu while open
    var videoCallCheckTimer: Timer?  // Timer for checking video call status

    // Timer state
    var isPaused: Bool = false
    var isAutoPaused: Bool = false  // Paused due to video call
    var nextBreakTime: Date = Date()
    var remainingWhenPaused: TimeInterval = 0  // Store remaining time when auto-paused

    init(scriptPath: String) {
        self.scriptPath = scriptPath
        super.init()
        setupMenuBar()
        setupNotifications()
        setupEyeBreakTimer()
    }

    func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        if let button = statusItem.button {
            button.title = "👁"
        }

        let menu = NSMenu()

        // Countdown display (disabled, just for display)
        countdownMenuItem = NSMenuItem(title: "Next break in: --:--", action: nil, keyEquivalent: "")
        countdownMenuItem.isEnabled = false
        menu.addItem(countdownMenuItem)

        menu.addItem(NSMenuItem.separator())

        // Take break now
        let takeBreakItem = NSMenuItem(title: "Take Break Now", action: #selector(takeBreakNow), keyEquivalent: "b")
        takeBreakItem.target = self
        menu.addItem(takeBreakItem)

        // Pause/Resume
        pauseMenuItem = NSMenuItem(title: "Pause Timer", action: #selector(togglePause), keyEquivalent: "p")
        pauseMenuItem.target = self
        menu.addItem(pauseMenuItem)

        menu.addItem(NSMenuItem.separator())

        // Quit
        let quitItem = NSMenuItem(title: "Quit", action: #selector(quitApp), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem.menu = menu
        menu.delegate = self

        // Check video call status every 10 seconds
        videoCallCheckTimer = Timer.scheduledTimer(withTimeInterval: 10.0, repeats: true) { [weak self] _ in
            self?.checkVideoCallStatus()
        }

        // Update status icon (not countdown, just pause status)
        updateStatusIcon()

        log("Menu bar indicator initialized")
    }

    // NSMenuDelegate - called when menu opens
    func menuWillOpen(_ menu: NSMenu) {
        updateCountdownDisplay()
        // Start rapid updates while menu is open
        // Must add to commonModes to work during menu tracking
        menuUpdateTimer = Timer(timeInterval: 0.5, repeats: true) { [weak self] _ in
            self?.updateCountdownDisplay()
        }
        RunLoop.main.add(menuUpdateTimer!, forMode: .common)
    }

    // NSMenuDelegate - called when menu closes
    func menuDidClose(_ menu: NSMenu) {
        menuUpdateTimer?.invalidate()
        menuUpdateTimer = nil
    }

    func updateStatusIcon() {
        if let button = statusItem.button {
            if isPaused || isAutoPaused {
                button.title = "👁 ⏸"
            } else {
                button.title = "👁"
            }
        }
    }

    func updateCountdownDisplay() {
        if isPaused || isAutoPaused {
            let pauseReason = isAutoPaused ? "paused (in call)" : "paused"
            countdownMenuItem.title = "Timer \(pauseReason)"
            return
        }

        let remaining = nextBreakTime.timeIntervalSince(Date())
        if remaining > 0 {
            let minutes = Int(remaining) / 60
            let seconds = Int(remaining) % 60
            countdownMenuItem.title = String(format: "Next break in: %02d:%02d", minutes, seconds)
        } else {
            countdownMenuItem.title = "Break time!"
        }
    }

    func isInVideoCall() -> Bool {
        let runningApps = NSWorkspace.shared.runningApplications

        // Check if Zoom or Teams is running
        for app in runningApps {
            if let bundleId = app.bundleIdentifier {
                // Zoom
                if bundleId.lowercased().contains("zoom.us") {
                    log("Video call detected: Zoom is running")
                    return true
                }
                // Microsoft Teams
                if bundleId.lowercased().contains("teams") || bundleId.lowercased().contains("msteams") {
                    log("Video call detected: MS Teams is running")
                    return true
                }
            }
        }

        // Check for Google Meet in browser tabs using AppleScript
        if hasGoogleMeetTab() {
            log("Video call detected: Google Meet tab open")
            return true
        }

        return false
    }

    func hasGoogleMeetTab() -> Bool {
        // Get list of running app names
        let runningApps = NSWorkspace.shared.runningApplications
        let runningAppNames = Set(runningApps.compactMap { $0.localizedName })

        // Browser name to AppleScript name mapping
        let browsers: [(processName: String, scriptName: String)] = [
            ("Brave Browser", "Brave Browser"),
            ("Google Chrome", "Google Chrome"),
            ("Safari", "Safari"),
            ("Firefox", "Firefox"),
            ("Arc", "Arc"),
            ("Microsoft Edge", "Microsoft Edge"),
        ]

        for browser in browsers {
            // Only check browsers that are actually running
            guard runningAppNames.contains(browser.processName) else {
                continue
            }

            let script = """
            tell application "\(browser.scriptName)"
                set tabURLs to ""
                try
                    repeat with w in windows
                        repeat with t in tabs of w
                            set tabURLs to tabURLs & (URL of t) & linefeed
                        end repeat
                    end repeat
                end try
                return tabURLs
            end tell
            """

            let appleScript = NSAppleScript(source: script)
            var error: NSDictionary?
            if let result = appleScript?.executeAndReturnError(&error) {
                let urls = result.stringValue ?? ""
                if urls.contains("meet.google.com") {
                    return true
                }
            }
        }

        return false
    }

    func checkVideoCallStatus() {
        let inCall = isInVideoCall()

        if inCall && !isAutoPaused && !isPaused {
            // Auto-pause: store remaining time
            remainingWhenPaused = nextBreakTime.timeIntervalSince(Date())
            isAutoPaused = true
            eyeBreakTimer?.invalidate()
            eyeBreakTimer = nil
            updateStatusIcon()
            log("Auto-paused: video call detected")
        } else if !inCall && isAutoPaused {
            // Auto-resume: restore remaining time
            isAutoPaused = false
            nextBreakTime = Date().addingTimeInterval(remainingWhenPaused)
            eyeBreakTimer = Timer.scheduledTimer(withTimeInterval: remainingWhenPaused, repeats: false) { [weak self] _ in
                self?.triggerEyeBreak()
                self?.setupEyeBreakTimer()
            }
            updateStatusIcon()
            log("Auto-resumed: video call ended, \(Int(remainingWhenPaused))s remaining")
        }
    }

    @objc func takeBreakNow() {
        log("Manual eye break triggered from menu bar")
        triggerEyeBreak()
    }

    @objc func togglePause() {
        isPaused = !isPaused

        if isPaused {
            eyeBreakTimer?.invalidate()
            eyeBreakTimer = nil
            pauseMenuItem.title = "Resume Timer"
            log("Eye break timer paused")
        } else {
            setupEyeBreakTimer()
            pauseMenuItem.title = "Pause Timer"
            log("Eye break timer resumed")
        }

        updateStatusIcon()
        updateCountdownDisplay()
    }

    @objc func quitApp() {
        log("Quit requested from menu bar")
        NSApplication.shared.terminate(nil)
    }

    func setupNotifications() {
        // Listen for screen unlock notification
        DistributedNotificationCenter.default().addObserver(
            self,
            selector: #selector(screenUnlocked),
            name: NSNotification.Name("com.apple.screenIsUnlocked"),
            object: nil
        )

        // Also listen for screen wake (display wake)
        NSWorkspace.shared.notificationCenter.addObserver(
            self,
            selector: #selector(screenWake),
            name: NSWorkspace.screensDidWakeNotification,
            object: nil
        )

        // Listen for session becoming active (user switched back)
        NSWorkspace.shared.notificationCenter.addObserver(
            self,
            selector: #selector(sessionBecameActive),
            name: NSWorkspace.sessionDidBecomeActiveNotification,
            object: nil
        )

        log("Unlock watcher started. Listening for screen unlock events...")
    }

    func setupEyeBreakTimer() {
        // Set the next break time
        nextBreakTime = Date().addingTimeInterval(eyeBreakIntervalSeconds)

        // Create a timer that fires every 20 minutes for eye breaks
        eyeBreakTimer = Timer.scheduledTimer(withTimeInterval: eyeBreakIntervalSeconds, repeats: true) { [weak self] _ in
            self?.triggerEyeBreak()
        }
        log("Eye break timer started. Will trigger every 20 minutes.")
    }

    func triggerEyeBreak() {
        let now = Date()

        // Check cooldown (don't trigger if quote just showed or eye break just showed)
        if now.timeIntervalSince(lastTriggerTime) < cooldownSeconds {
            log("Skipping eye break - quote display cooldown active")
            return
        }
        if now.timeIntervalSince(lastEyeBreakTriggerTime) < cooldownSeconds {
            log("Skipping eye break - eye break cooldown active")
            return
        }

        lastEyeBreakTriggerTime = now
        nextBreakTime = now.addingTimeInterval(eyeBreakIntervalSeconds)
        log("Triggering 20-20-20 eye break")

        let task = Process()
        task.launchPath = "/bin/bash"
        task.arguments = [scriptPath, "--eye-break"]

        do {
            try task.run()
        } catch {
            log("Error launching eye break: \(error)")
        }
    }

    @objc func screenUnlocked(_ notification: Notification) {
        triggerQuoteApp(reason: "screen unlock")
    }

    @objc func screenWake(_ notification: Notification) {
        triggerQuoteApp(reason: "screen wake")
    }

    @objc func sessionBecameActive(_ notification: Notification) {
        triggerQuoteApp(reason: "session active")
    }

    func triggerQuoteApp(reason: String) {
        let now = Date()

        // Check cooldown to prevent multiple triggers
        if now.timeIntervalSince(lastTriggerTime) < cooldownSeconds {
            log("Skipping trigger (\(reason)) - cooldown active")
            return
        }

        lastTriggerTime = now
        log("Triggering quote app: \(reason)")

        let task = Process()
        task.launchPath = "/bin/bash"
        task.arguments = [scriptPath]

        do {
            try task.run()
        } catch {
            log("Error launching quote app: \(error)")
        }
    }

    func run() {
        // Keep the app running - must use NSApplication.run() for menu events to work
        NSApplication.shared.run()
    }
}

// Main entry point
let args = CommandLine.arguments
guard args.count > 1 else {
    log("Usage: unlock_watcher <path-to-run-script>")
    exit(1)
}

let scriptPath = args[1]

// Verify the script exists
guard FileManager.default.fileExists(atPath: scriptPath) else {
    log("Error: Script not found at \(scriptPath)")
    exit(1)
}

// Setup as menu bar app (no dock icon)
NSApplication.shared.setActivationPolicy(.accessory)

let watcher = ScreenUnlockWatcher(scriptPath: scriptPath)
watcher.run()
