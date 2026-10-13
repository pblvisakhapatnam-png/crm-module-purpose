import type { SelectHTMLAttributes } from "react";

import { currencyChoices } from "./currency";

type CurrencySelectProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "value" | "onChange" | "children"> & {
  value: string;
  onChange: (currencyCode: string) => void;
  /** Adds a first, empty choice with this label, for a field where no currency is a valid answer. */
  blankLabel?: string;
};

/** Every currency box: a choice from the one list in ./currency, never free text. */
export default function CurrencySelect({ value, onChange, blankLabel, ...selectProps }: CurrencySelectProps) {
  return (
    <select {...selectProps} value={value} onChange={(event) => onChange(event.target.value)}>
      {blankLabel !== undefined ? <option value="">{blankLabel}</option> : null}
      {currencyChoices(value).map((choice) => (
        <option key={choice.value} value={choice.value}>
          {choice.label}
        </option>
      ))}
    </select>
  );
}
