interface Props {
  id: string;
  type: React.HTMLInputTypeAttribute;
  name: string;
  placeholder: string;
  label: string;
  required?: boolean;
}

export const InputPlacetop: React.FC<Props & React.InputHTMLAttributes<HTMLInputElement>> = ({
  id = "",
  type = "",
  name = "",
  placeholder = "",
  label = "",
  required = false,
  ...props
}) => {
  return (
    <div className="form-control form-control--fullwidth">
      <div className="text-field">
        <input
          id={id}
          className="input-base__input"
          type={type}
          name={name}
          placeholder={placeholder}
          required={required}
          {...props}
        />
        <label htmlFor={id} className="text-field__label">
          {label}
        </label>
      </div>
    </div>
  );
};
