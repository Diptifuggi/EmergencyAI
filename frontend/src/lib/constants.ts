// @ts-nocheck
// Prefer an explicit VITE_API_BASE_URL if provided. If not present, use a relative path so Vite dev server proxy can forward requests.
export const API_BASE_URL = (import.meta as any).env.VITE_API_BASE_URL || '/api/v1'

export const PRIORITY_CONFIG = {
  Critical:  { bg: "bg-red-100",    text: "text-red-800",    dot: "bg-red-600",    border: "border-l-red-600"   },
  "Very High":{ bg: "bg-orange-100", text: "text-orange-800", dot: "bg-orange-500",  border: "border-l-orange-500"},
  High:      { bg: "bg-amber-100",   text: "text-amber-800",  dot: "bg-amber-500",   border: "border-l-amber-500" },
  Moderate:  { bg: "bg-green-100",   text: "text-green-800",  dot: "bg-green-600",   border: "border-l-green-600" },
  Low:       { bg: "bg-blue-100",    text: "text-blue-800",   dot: "bg-blue-500",    border: "border-l-blue-500"  },
}

export const CALL_STATUSES = ["Pending", "Processing", "Assigned", "Resolved"]

export const CATEGORIES = [
  "Road Accident","Medical Emergency","Fire","Women Safety",
  "Child Abuse","Cyber Crime","Natural Disaster","Other"
]

export const DEPARTMENTS = ["Police","Fire","Ambulance","Women Team","Child Protection Team"]

export const INDIA_EMERGENCY_NUMBERS = [
  { number: "112", label: "ERSS" },
  { number: "100", label: "Police" },
  { number: "101", label: "Fire" },
  { number: "108", label: "Ambulance" },
  { number: "181", label: "Women" },
  { number: "1098", label: "Child" },
]

export const SOP_ACTIONS: Record<string, string[]> = {
  "Road Accident": [
    "Dispatch 108 Ambulance to location",
    "Inform Traffic Police (SSP)",
    "Alert nearest hospital emergency",
    "Notify Highway Patrol / NHAI",
    "Inform Transport Department",
  ],
  "Medical Emergency": [
    "Dispatch 108 Ambulance",
    "Inform Emergency Medical Services",
    "Alert ICU bed availability",
    "Inform Health Department",
    "Notify nearest PHC/CHC",
  ],
  "Fire": [
    "Dispatch Fire Brigade (101)",
    "Inform Health Dept (EMS & Public Health)",
    "Alert Search & Rescue team",
    "Inform PWD (debris clearance)",
    "Notify Civil Supplies (relief)",
  ],
  "Women Safety": [
    "Dispatch Police + Women Team",
    "Inform Women & Child Development Dept",
    "Alert One Stop Centre",
    "Notify Women Helpline 181",
  ],
  "Child Abuse": [
    "Dispatch Police + Child Protection",
    "Inform DCPU (District Child Protection Unit)",
    "Alert CWC (Child Welfare Committee)",
    "Notify Childline 1098",
  ],
  "Natural Disaster": [
    "Inform SSP Traffic (Communication)",
    "Alert Health Dept (EMS & Public Health)",
    "Dispatch Fire (Search & Rescue, HazMat)",
    "Inform Transport Department",
    "Notify PWD (debris clearance)",
    "Inform Women & Child Development",
    "Alert Civil Supplies (food & relief)",
    "Notify Water Supply & Sanitation",
  ],
  "Cyber Crime": [
    "File cyber complaint online (cybercrime.gov.in)",
    "Inform Cyber Cell",
    "Notify Bank if financial fraud",
    "Alert State Cyber Police",
  ],
  "Other": [
    "Assess situation with caller",
    "Dispatch nearest available unit",
    "Inform relevant department",
  ],
}
