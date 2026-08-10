import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../shared/api/client";
import { Icon } from "../../shared/components/Icon";

export function RaiseEnquiryPage() {
  const [config, setConfig] = useState(null);
  const [values, setValues] = useState({});
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/client/enquiry-form-config").then(setConfig).catch((err) => setError(err.message));
  }, []);

  function setValue(key, value) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      const enquiry = await api.post("/client/enquiries", values);
      navigate(`/portal/enquiries/${enquiry.id}`);
    } catch (err) {
      setError(err.message);
    }
  }

  if (!config) return <p className="page-loading">{error || "Loading form..."}</p>;

  return (
    <div>
      <div className="page-header">
        <h2>Raise a new enquiry</h2>
        <p className="subtitle">Tell us about the vehicle and job, and we'll come back with a quote.</p>
      </div>

      <section className="card">
        <div className="card-header">
          <div className="card-header-title">
            <div className="icon-badge">
              <Icon name="key" size={16} />
            </div>
            <h3>Vehicle & Job Information</h3>
          </div>
        </div>

        <form onSubmit={submit} className="dynamic-form">
          {config.service_types.length > 0 && (
            <label>
              Service type
              <select onChange={(e) => setValue("service_type_id", e.target.value)}>
                <option value="">Select...</option>
                {config.service_types.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {config.fields.map((field) => (
            <FormField key={field.field_key} field={field} onChange={(v) => setValue(field.field_key, v)} />
          ))}

          {error && <p className="form-error">{error}</p>}
          <button type="submit">Submit enquiry</button>
        </form>
      </section>
    </div>
  );
}

function FormField({ field, onChange }) {
  const commonProps = { required: field.is_required, onChange: (e) => onChange(e.target.value) };

  return (
    <label>
      {field.label}
      {field.is_required && " *"}
      {field.field_type === "textarea" && <textarea {...commonProps} />}
      {field.field_type === "select" && (
        <select {...commonProps}>
          <option value="">Select...</option>
          {(field.options || []).map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      )}
      {field.field_type === "date" && <input type="date" {...commonProps} />}
      {field.field_type === "checkbox" && <input type="checkbox" onChange={(e) => onChange(e.target.checked)} />}
      {(field.field_type === "text" || !["textarea", "select", "date", "checkbox"].includes(field.field_type)) && (
        <input type="text" {...commonProps} />
      )}
    </label>
  );
}
