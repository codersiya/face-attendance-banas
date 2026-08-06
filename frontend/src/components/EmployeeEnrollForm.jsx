import { useEffect, useState } from "react";
import CameraCapture from "./CameraCapture.jsx";
import { createEmployee, enrollFaces, validatePhoto, extractErrorMessage } from "../api/employeeApi.js";

const emptyForm = {
  emp_id: "",
  emp_code: "",
  employee_name: "",
  department: "",
  designation: "",
  shift_start_time: "09:00",
  shift_end_time: "18:00",
  grace_time_minutes: 10,
  late_entry_minutes: 15,
  overtime_rules: "",
};

const POSES = [
  { key: "front", label: "Front" },
  { key: "left", label: "Left profile" },
  { key: "right", label: "Right profile" },
];

const emptyValidation = { front: "idle", left: "idle", right: "idle" };
const emptyValidationMsg = { front: "", left: "", right: "" };

export default function EmployeeEnrollForm() {
  const [form, setForm] = useState(emptyForm);
  const [captures, setCaptures] = useState({ front: null, left: null, right: null });
  const [previewUrls, setPreviewUrls] = useState({ front: null, left: null, right: null });
  const [validation, setValidation] = useState(emptyValidation);
  const [validationMsg, setValidationMsg] = useState(emptyValidationMsg);
  const [step, setStep] = useState("form"); // form -> photos -> submitting -> done
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [toast, setToast] = useState(null); // { type: "error"|"success", text }

  // Auto-dismiss the pop-up toast after a few seconds.
  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  const updateField = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleDetailsSubmit = (e) => {
    e.preventDefault();
    setStep("photos");
  };

  // Called right after a pose is captured. Runs pose-aware face detection
  // immediately - so an incorrect angle is caught right here, with a pop-up,
  // instead of surfacing at final submit time.
  const handleCapture = (poseKey) => async (blob) => {
    if (blob === null) {
      setCaptures((prev) => ({ ...prev, [poseKey]: null }));
      setPreviewUrls((prev) => ({ ...prev, [poseKey]: null }));
      setValidation((prev) => ({ ...prev, [poseKey]: "idle" }));
      setValidationMsg((prev) => ({ ...prev, [poseKey]: "" }));
      return;
    }

    const previewUrl = URL.createObjectURL(blob);
    setCaptures((prev) => ({ ...prev, [poseKey]: blob }));
    setPreviewUrls((prev) => ({ ...prev, [poseKey]: previewUrl }));
    setValidation((prev) => ({ ...prev, [poseKey]: "checking" }));
    setValidationMsg((prev) => ({ ...prev, [poseKey]: "" }));

    try {
      const { valid, message } = await validatePhoto(blob, poseKey);
      if (valid) {
        setValidation((prev) => ({ ...prev, [poseKey]: "valid" }));
        setValidationMsg((prev) => ({ ...prev, [poseKey]: message }));
      } else {
        setValidation((prev) => ({ ...prev, [poseKey]: "invalid" }));
        setValidationMsg((prev) => ({ ...prev, [poseKey]: message }));
        setCaptures((prev) => ({ ...prev, [poseKey]: null }));
        setPreviewUrls((prev) => ({ ...prev, [poseKey]: null }));
        setToast({ type: "error", text: `${poseLabel(poseKey)}: ${message}` });
      }
    } catch (err) {
      const message = extractErrorMessage(err);
      setValidation((prev) => ({ ...prev, [poseKey]: "invalid" }));
      setValidationMsg((prev) => ({ ...prev, [poseKey]: message }));
      setCaptures((prev) => ({ ...prev, [poseKey]: null }));
      setPreviewUrls((prev) => ({ ...prev, [poseKey]: null }));
      setToast({ type: "error", text: `${poseLabel(poseKey)}: ${message}` });
    }
  };

  const poseLabel = (key) => POSES.find((p) => p.key === key)?.label ?? key;

  // Only enable "Enroll employee" once every pose has passed validation.
  const allValid = POSES.every((p) => validation[p.key] === "valid");

  const handleFinalSubmit = async () => {
    setError("");
    setStep("submitting");
    try {
      const employee = await createEmployee({
        ...form,
        emp_id: form.emp_id.trim(),
        emp_code: form.emp_code.trim(),
        grace_time_minutes: Number(form.grace_time_minutes),
        late_entry_minutes: Number(form.late_entry_minutes),
      });

      const enrollResult = await enrollFaces(employee.emp_id, captures);

      setResult({ employee, enrollResult });
      setStep("done");
    } catch (err) {
      const message = extractErrorMessage(err);
      setError(message);
      setToast({ type: "error", text: message });
      setStep("form");
    }
  };

  const handleReset = () => {
    setForm(emptyForm);
    setCaptures({ front: null, left: null, right: null });
    setPreviewUrls({ front: null, left: null, right: null });
    setValidation(emptyValidation);
    setValidationMsg(emptyValidationMsg);
    setError("");
    setResult(null);
    setStep("form");
  };

  return (
    <div className="enroll-card">
      {toast && (
        <div className={`toast toast--${toast.type}`} role="alert">
          {toast.text}
        </div>
      )}

      <div className="enroll-card__steps">
        <StepDot active={step === "form"} done={step !== "form"} label="1. Details" />
        <StepDot
          active={step === "photos" || step === "submitting"}
          done={step === "done"}
          label="2. Face capture"
        />
        <StepDot active={step === "done"} done={step === "done"} label="3. Confirm" />
      </div>

      {step === "form" && (
        <form className="enroll-form" onSubmit={handleDetailsSubmit}>
          <h2>Employee details</h2>

          {error && <div className="alert alert--error">{error}</div>}

          <div className="enroll-form__grid">
            <Field label="Employee ID" required>
              <input
                value={form.emp_id}
                onChange={updateField("emp_id")}
                placeholder="e.g. 0091"
                pattern="[A-Za-z0-9_-]+"
                title="Letters, numbers, hyphens and underscores only"
                required
              />
            </Field>
            <Field label="Employee Code" required>
              <input
                value={form.emp_code}
                onChange={updateField("emp_code")}
                placeholder="e.g. EMP0091"
                pattern="[A-Za-z0-9_-]+"
                title="Letters, numbers, hyphens and underscores only"
                required
              />
            </Field>
            <Field label="Employee name" required>
              <input value={form.employee_name} onChange={updateField("employee_name")} required />
            </Field>
            <Field label="Department" required>
              <input value={form.department} onChange={updateField("department")} required />
            </Field>
            <Field label="Designation" required>
              <input value={form.designation} onChange={updateField("designation")} required />
            </Field>
            <Field label="Shift start time" required>
              <input
                type="time"
                value={form.shift_start_time}
                onChange={updateField("shift_start_time")}
                required
              />
            </Field>
            <Field label="Shift end time" required>
              <input
                type="time"
                value={form.shift_end_time}
                onChange={updateField("shift_end_time")}
                required
              />
            </Field>
            <Field label="Grace time (minutes)">
              <input
                type="number"
                min="0"
                value={form.grace_time_minutes}
                onChange={updateField("grace_time_minutes")}
              />
            </Field>
            <Field label="Late entry threshold (minutes)">
              <input
                type="number"
                min="0"
                value={form.late_entry_minutes}
                onChange={updateField("late_entry_minutes")}
              />
            </Field>
            <Field label="Overtime rules" fullWidth>
              <textarea
                rows={3}
                placeholder="e.g. 1.5x pay after 8 hrs on weekdays, 2x on holidays"
                value={form.overtime_rules}
                onChange={updateField("overtime_rules")}
              />
            </Field>
          </div>

          <div className="enroll-form__actions">
            <button type="submit" className="btn btn--primary">
              Continue to face capture
            </button>
          </div>
        </form>
      )}

      {(step === "photos" || step === "submitting") && (
        <div className="enroll-photos">
          <h2>Capture 3 face images</h2>
          <p className="enroll-photos__hint">
            Center your face in the oval. For "Left profile" / "Right profile", follow the arrow
            and turn your head about 30-45° - not a full side-on turn. Each photo is checked
            immediately after capture; if the angle or lighting isn't right, you'll be told exactly
            what to fix and asked to retake it before continuing.
          </p>

          {error && <div className="alert alert--error">{error}</div>}

          <div className="enroll-photos__grid">
            {POSES.map((pose) => (
              <CameraCapture
                key={pose.key}
                label={pose.label}
                poseKey={pose.key}
                onCapture={handleCapture(pose.key)}
                capturedPreviewUrl={previewUrls[pose.key]}
                validationStatus={validation[pose.key]}
                validationMessage={validationMsg[pose.key]}
              />
            ))}
          </div>

          <div className="enroll-form__actions">
            <button type="button" className="btn btn--ghost" onClick={() => setStep("form")}>
              Back
            </button>
            <button
              type="button"
              className="btn btn--primary"
              disabled={!allValid || step === "submitting"}
              onClick={handleFinalSubmit}
            >
              {step === "submitting" ? "Enrolling..." : "Enroll employee"}
            </button>
          </div>
        </div>
      )}

      {step === "done" && result && (
        <div className="enroll-done">
          <div className="alert alert--success">{result.enrollResult.message}</div>
          <dl className="enroll-done__summary">
            <dt>Employee ID</dt>
            <dd>{result.employee.emp_id}</dd>
            <dt>Employee Code</dt>
            <dd>{result.employee.emp_code}</dd>
            <dt>Name</dt>
            <dd>{result.employee.employee_name}</dd>
            <dt>Department</dt>
            <dd>{result.employee.department}</dd>
            <dt>Designation</dt>
            <dd>{result.employee.designation}</dd>
            <dt>Shift</dt>
            <dd>
              {result.employee.shift_start_time} - {result.employee.shift_end_time}
            </dd>
          </dl>
          <button type="button" className="btn btn--primary" onClick={handleReset}>
            Enroll another employee
          </button>
        </div>
      )}
    </div>
  );
}

function Field({ label, required, fullWidth, children }) {
  return (
    <label className={`field ${fullWidth ? "field--full" : ""}`}>
      <span className="field__label">
        {label}
        {required && <span className="field__required">*</span>}
      </span>
      {children}
    </label>
  );
}

function StepDot({ active, done, label }) {
  return (
    <div className={`step-dot ${active ? "step-dot--active" : ""} ${done ? "step-dot--done" : ""}`}>
      <span className="step-dot__marker" />
      <span className="step-dot__label">{label}</span>
    </div>
  );
}