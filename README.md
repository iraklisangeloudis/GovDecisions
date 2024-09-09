# Python Script Scheduled Execution

This repository contains a Python script that is scheduled to run every hour using Windows Task Scheduler. The script runs silently in the background without opening any visible Command Prompt windows.

## Getting Started

### Prerequisites

* **Python**: Ensure Python is installed and added to your system's PATH.
* **Windows**: The steps below are specific to Windows 11.

### Setup Instructions

1. **Clone the Repository**:
   ```sh
   git clone https://github.com/iraklisangeloudis/todays_decisions.git
   cd todays_decisions
   ```

2. **Modify the Script**:
   * Update the Python script (`todays_decisions.py`) to perform your desired task.
   * Ensure the correct file paths are used within the script.

3. **Create a Batch File**:
   * Create a batch file to run the Python script:
     ```batch
     @echo off
     python "C:\path\to\your\todays_decisions.py"
     ```
   * Save this as `run_script.bat`.

4. **Create a VBS Script**:
   * To run the batch file silently in the background, create a VBS script:
     ```vbs
     Set WshShell = CreateObject("WScript.Shell")
     WshShell.Run chr(34) & "C:\path\to\your\run_script.bat" & Chr(34), 0
     Set WshShell = Nothing
     ```
   * Save this as `run_script_hidden.vbs`.

5. **Set Up Task Scheduler**:
   * Open Task Scheduler on your Windows machine.
   * Create a new task:
     * **General Tab**: Name the task and set it to run only when user is logged on.
     * **Triggers Tab**: Set the task to repeat every hour.
     * **Actions Tab**: Point the task to the `run_script_hidden.vbs` file.
   * Save and test the task to ensure it runs as expected.

## Testing the Setup

* Right-click on the task in Task Scheduler and select "Run" to test the task. The script should execute without showing any visible windows.

## Troubleshooting

* **Task not running**: Ensure your Python script runs correctly when executed manually. Check Task Scheduler history for errors.
* **Window appears**: If a window appears during execution, double-check that the task is pointing to the `.vbs` file and not the `.bat` file.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

Law 3861/2010 "Strengthening transparency with the mandatory posting of laws
and acts of governmental, administrative and self-governing bodies in
internet "Diavgeia Program" and other provisions".

Ν. 3861/2010 «Ενίσχυση της διαφάνειας με την υποχρεωτική ανάρτηση νόμων
και πράξεων των κυβερνητικών, διοικητικών και αυτοδιοικητικών οργάνων στο
διαδίκτυο «Πρόγραμμα Διαύγεια» και άλλες διατάξεις», (Α΄ 112)

This script is made for personal use. 
