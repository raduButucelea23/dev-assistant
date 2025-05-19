# RAG Smoke Test Queries

This document contains informal natural language queries for testing retrieval and relevance of the RAG application across different document types.

## Catalogues

### IVI Signal Database
- **Prompt 1**: "What are the values defined for the IVI_System_Status signal?"
  
  **Expected**: "The IVI system transmits its general status through the IVI_System_Status signal, which includes system state (INITIALIZING, RUNNING, DEGRADED, ERROR), error code, and app status for navigation and media with a cycle time of 200ms."
  
  **Source**: data/catalogues/ivi_signal_database.json, signal name: IVI_System_Status

- **Prompt 2**: "What details does the battery management system send to the IVI about charging status?"
  
  **Expected**: "The BMS sends charging status to the IVI through the BMS_ChargingStatus signal, including charging state, charge percentage, range in km, charging rate in kW, minutes remaining, and error code."
  
  **Source**: data/catalogues/ivi_signal_database.json, signal name: BMS_ChargingStatus

- **Prompt 3**: "What data do the parking distance control sensors provide to the IVI system?"
  
  **Expected**: "The PDC sensors provide distance information through the PDC_Sensor_Data signal, containing distance values (0-250cm) for front_left, front_center, front_right, rear_left, rear_center, rear_right, and status (ACTIVE, DEACTIVATED, ERROR)."
  
  **Source**: data/catalogues/ivi_signal_database.json, signal name: PDC_Sensor_Data

- **Prompt 4**: "What commands can be sent to control media playback via the IVI system?"
  
  **Expected**: "Media playback can be controlled through the MEDIA_Control_Command signal with commands including PLAY, PAUSE, NEXT, PREVIOUS, VOLUME_UP, and VOLUME_DOWN."
  
  **Source**: data/catalogues/ivi_signal_database.json, signal name: MEDIA_Control_Command

- **Prompt 5**: "How does the IVI system report its self-test results during startup?"
  
  **Expected**: "The IVI system reports startup self-test results through the IVI_SelfTest_Result signal, which includes overall_result (PASS, FAIL, PARTIAL_PASS), detailed component_results with test results and error codes, and a timestamp."
  
  **Source**: data/catalogues/ivi_signal_database.json, signal name: IVI_SelfTest_Result

- **Prompt 6**: "Which commands can the IVI system send to the Body Control Module (BCM)?"
  
  **Expected**: "The IVI system can send several commands to the BCM including DOOR_Lock_Command, WINDOW_Position_Command, TRUNK_Command, and LIGHT_Control_Request."
  
  **Source**: data/catalogues/ivi_signal_database.json, signals with source: "IVI" and targets including "BCM"

- **Prompt 7**: "Which IVI signals have a defined cycle time of 1000ms?"
  
  **Expected**: "IVI signals with a 1000ms cycle time include IVI_Heartbeat, BMS_EnergyConsumption, IVI_Memory_Status, IVI_Performance_Metrics, and IVI_Network_Status."
  
  **Source**: data/catalogues/ivi_signal_database.json, signals with cycle_time_ms: 1000

### IVI Diagnostic Catalogue
- **Prompt 1**: "What are the possible root causes of the B2001 Display Panel Malfunction DTC in the IVI system?"
  
  **Expected**: "The possible root causes for B2001 Display Panel Malfunction include LCD controller failure, touch controller malfunction, display cable disconnection, and display power supply issue."
  
  **Source**: data/catalogues/IVI_Diagnostic_Catalogue.odx-c, DTC ID="DTC_B2001" section

- **Prompt 2**: "What is the diagnostic address for the IVI system?"
  
  **Expected**: "The IVI system has a diagnostic address of 0x760, with a functional group address of 0x7DF and a response address of 0x768."
  
  **Source**: data/catalogues/IVI_Diagnostic_Catalogue.odx-c, DIAG-COMM ID="DC_IVI_MAIN" section

- **Prompt 3**: "Is there a DTC raised in case of a problem with the connectivity hardware?"
  
  **Expected**: "Yes, DTC B2000 (Connectivity Module Malfunction) is raised when there are issues with the connectivity hardware components."
  
  **Source**: data/catalogues/IVI_Diagnostic_Catalogue.odx-c, DTC ID="DTC_B2000" section

- **Prompt 4**: "Does DTC B2000 support snapshot data and aging counter?"
  
  **Expected**: "Yes, DTC B2000 supports both snapshot data capture of system conditions when the error occurred and an aging counter to track intermittent fault frequency."
  
  **Source**: data/catalogues/IVI_Diagnostic_Catalogue.odx-c, DTC ID="DTC_B2000" section

- **Prompt 5**: "What are the possible causes of DTC B2000?"
  
  **Expected**: "Possible causes of DTC B2000 include Wi-Fi module failure, cellular modem hardware fault, Bluetooth module malfunction, antenna disconnection, and power supply issues to the connectivity components."
  
  **Source**: data/catalogues/IVI_Diagnostic_Catalogue.odx-c, DTC ID="DTC_B2000" section

## Requirements

### FMEA Documents
- **Prompt 1**: "What are the potential causes of camera feed freezing in the IVI system?"
  
  **Expected**: "The potential causes of camera feed freeze or interruption include camera hardware failure, image processing software crash, and video buffer overflow."
  
  **Source**: data/requirements/camera-system-integration-fmea.json, failureMode id: FM-CSI-03, potentialCauses field

- **Prompt 2**: "What is the safety goal for the camera system integration related to distance information?"
  
  **Expected**: "Safety goal SG-CSI-02 states: 'The Camera System Integration shall clearly present distance and trajectory information to prevent driver misinterpretation' with an ASIL B rating."
  
  **Source**: data/requirements/camera-system-integration-fmea.json, safetyGoals section, id: SG-CSI-02

- **Prompt 3**: "What is the error mode for the highest camera RPN?"
  
  **Expected**: "The error mode with the highest Risk Priority Number (RPN) in the camera system is 'Distorted or Incorrect Camera Image' with failure mode ID FM-CSI-03."
  
  **Source**: data/requirements/camera-system-integration-fmea.json, failureMode id: FM-CSI-03, riskPriorityNumber field

- **Prompt 4**: "What is the safety goal associated with the error mode for the highest camera RPN?"
  
  **Expected**: "The safety goal associated with the highest RPN camera error mode (Distorted or Incorrect Camera Image) is SG-CSI-02: 'The Camera System Integration shall clearly present distance and trajectory information to prevent driver misinterpretation' with ASIL B rating."
  
  **Source**: data/requirements/camera-system-integration-fmea.json, safetyGoals section, id: SG-CSI-02, relatedFailureModes field

- **Prompt 5**: "What is the lowest RPN for the software download feature?"
  
  **Expected**: "The lowest Risk Priority Number (RPN) for the software download feature is 24, associated with the failure mode 'Download Progress Indicator Malfunction'."
  
  **Source**: data/requirements/software-download-fmea.json, failureMode id: FM-SD-05, riskPriorityNumber field

- **Prompt 6**: "What is the highest ASIL associated to software download goals?"
  
  **Expected**: "The highest ASIL associated with software download goals is ASIL D, assigned to safety goal SG-SD-01: 'The Software Download function shall preserve critical vehicle functionality during and after updates'."
  
  **Source**: data/requirements/software-download-fmea.json, safetyGoals section, id: SG-SD-01, asilRating field

### TARA Threat Scenarios
- **Prompt 1**: "How might an attacker spoof GPS signals to affect the navigation system?"
  
  **Expected**: "An attacker might use a portable GPS simulator or Software-Defined Radio (SDR) to broadcast counterfeit GPS signals that are stronger than authentic satellite signals, causing the vehicle's GPS receiver to lock onto the spoofed signals."
  
  **Source**: data/requirements/navigation-tara-threat-scenarios.json, threatScenarios, id: TS-NAV-02

- **Prompt 2**: "What attack vectors exist for manipulating the navigation map database?"
  
  **Expected**: "Attack vectors include: compromised map update server, man-in-the-middle attack during updates, and local manipulation via USB containing compromised map data for manual update."
  
  **Source**: data/requirements/navigation-tara-threat-scenarios.json, threatScenarios, id: TS-NAV-01, attackVectors field

### TARA Impact Analysis
- **Prompt 1**: "What could be the impact of a navigation history data breach?"
  
  **Expected**: "A navigation history data breach could reveal sensitive information about user travel patterns, frequently visited locations, and potentially home and work addresses, leading to privacy violations and potential physical security risks."
  
  **Source**: data/requirements/navigation-tara-impact-analysis.json, impacts related to TS-NAV-03

- **Prompt 2**: "What safety impacts could result from GPS signal spoofing?"
  
  **Expected**: "GPS signal spoofing could lead to incorrect route guidance, misleading the driver about their actual position, potentially directing them to hazardous areas or causing confusion that results in unsafe driving maneuvers."
  
  **Source**: data/requirements/navigation-tara-impact-analysis.json, impacts related to TS-NAV-02

### TARA Risk Assessment
- **Prompt 1**: "What methodology is used for assessing cybersecurity risks in the navigation system?"
  
  **Expected**: "The risk assessment uses the ISO 21434 Risk Assessment methodology, evaluating risk as a combination of impact and attack feasibility."
  
  **Source**: data/requirements/navigation-tara-risk-assessment.json, methodology section

- **Prompt 2**: "How feasible is a GPS spoofing attack according to the threat assessment?"
  
  **Expected**: "The GPS spoofing attack is assessed as having Medium feasibility, considering factors like the requirement for specialized equipment (portable GPS simulator or SDR) and the need for physical proximity to the vehicle."
  
  **Source**: data/requirements/navigation-tara-risk-assessment.json, threatAssessments for TS-NAV-02

### IVI System Specification
- **Prompt 1**: "How long should it take for the IVI system to start up after ignition?"
  
  **Expected**: "According to requirement FR-PWR-003, the IVI system shall transition from STANDBY to ON state within 3 seconds of ignition status changing to IGN_ON."
  
  **Source**: data/requirements/IVI-system-spec-sysml3.md, section 3.1 Power Management, requirement FR-PWR-003

- **Prompt 2**: "What happens when the IVI navigation system loses GPS signal in a tunnel?"
  
  **Expected**: "According to requirement FR-NAV-001, the IVI navigation system shall continue providing turn-by-turn guidance for at least 1km when GPS signal is lost, such as in tunnels."
  
  **Source**: data/requirements/IVI-system-spec-sysml3.md, section 3.4 Navigation and Location Services, requirement FR-NAV-001

## Standards

### ISO 21434
- **Prompt 1**: "What cybersecurity standard is referenced in the IVI system specification?"
  
  **Expected**: "ISO 21434: Road Vehicles – Cybersecurity Engineering is referenced in the IVI System Specification document."
  
  **Source**: data/requirements/IVI-system-spec-sysml3.md, section 1.5 Reference Documents

- **Prompt 2**: "How is ISO 21434 used in threat assessment?"
  
  **Expected**: "ISO 21434 is used as the basis for the risk assessment methodology, evaluating cybersecurity risks as a combination of impact and attack feasibility."
  
  **Source**: data/requirements/navigation-tara-risk-assessment.json, methodology section

### ISO 14229
- **Prompt 1**: "What diagnostic communication standards are used in the IVI system?"
  
  **Expected**: "The IVI system uses ISO 14229 (referenced as ISO_15765_3_on_ISO_15765_2 or UDS on CAN) for diagnostic communications."
  
  **Source**: data/catalogues/IVI_Diagnostic_Catalogue.odx-c, COMPARAM-SPEC section

- **Prompt 2**: "What diagnostic services are defined for the IVI system?"
  
  **Expected**: "The IVI diagnostic catalogue defines diagnostic services including READ_DTC_INFO (Read DTC Information, UDS Service 0x19) and CLEAR_DTC (Clear Diagnostic Information, UDS Service 0x14)."
  
  **Source**: data/catalogues/IVI_Diagnostic_Catalogue.odx-c, DIAG-SERVICES section

## Entities

### Entities JSON
- **Prompt 1**: "What is the IVI HMI component described as in the entities database?"
  
  **Expected**: "The IVI HMI is described as 'Human Machine Interface component of the IVI system' in the entities database."
  
  **Source**: data/entities.json, target_entities section, name: "IVI HMI"

- **Prompt 2**: "What entities are related to the vehicle's climate control?"
  
  **Expected**: "The entities related to climate control include 'CCS' (Climate Control System) and potentially 'HVAC Control' components mentioned in reference documents."
  
  **Source**: data/entities.json, source_entities and target_entities sections 