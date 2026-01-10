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

class ScreenUnlockWatcher: NSObject {
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
    var updateTimer: Timer?

    // Timer state
    var isPaused: Bool = false
    var nextBreakTime: Date = Date()

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

        // Update countdown every second
        updateTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.updateCountdownDisplay()
        }

        log("Menu bar indicator initialized")
    }

    func updateCountdownDisplay() {
        if isPaused {
            countdownMenuItem.title = "Timer paused"
            if let button = statusItem.button {
                button.title = "👁 ⏸"
            }
            return
        }

        let remaining = nextBreakTime.timeIntervalSince(Date())
        if remaining > 0 {
            let minutes = Int(remaining) / 60
            let seconds = Int(remaining) % 60
            countdownMenuItem.title = String(format: "Next break in: %02d:%02d", minutes, seconds)
            if let button = statusItem.button {
                button.title = "👁"
            }
        } else {
            countdownMenuItem.title = "Break time!"
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
