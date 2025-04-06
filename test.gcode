; Test G-code for Virtual Printer in OctoPrint
; This file is for testing basic movements and commands

G21         ; Set units to millimeters
G90         ; Use absolute positioning
M82         ; Set extruder to absolute mode

; Home all axes
G28

; Heat commands (for simulation purposes – may be ignored by virtual printer)
M104 S200   ; Set extruder temperature to 200°C
M140 S60    ; Set bed temperature to 60°C
M109 S200   ; Wait for extruder to reach 200°C
M190 S60    ; Wait for bed to reach 60°C

; Start print moves
G92 E0      ; Reset extruder distance
G1 F200 E3  ; Prime the extruder
G1 X50 Y50 F3000  ; Move to start position

; Draw a square while extruding
G1 X100 Y50 E5 F1800   ; Move to the right while extruding
G1 X100 Y100 E5        ; Move upward while extruding
G1 X50 Y100 E5         ; Move left while extruding
G1 X50 Y50 E5          ; Complete the square

; Finish up
M104 S0    ; Turn off extruder heater
M140 S0    ; Turn off bed heater
G28 X0     ; Home X axis
M84        ; Disable motors

; End of test G-code
