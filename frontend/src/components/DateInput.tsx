import type { InputHTMLAttributes } from "react";

// Every date box in the application. A browser date box otherwise lets its year run on to five or six
// digits; with a maximum it stops at four (owner's screen checks, 22 September 2026 on the Work Order page and
// 28 September 2026 on the certificate pages). A page gives its own maximum where it has one, such as today for
// a day that cannot be in the future. `withTime` makes it a date-and-time box. The server remains the control;
// this only stops the browser offering a date nobody means. A test fails when a page uses a plain date box
// instead (dateInputs.test.ts).

/** The last day a date box offers: a four-digit year. */
export const DATE_INPUT_MAX = "9999-12-31";
/** The same for a date-and-time box. */
export const DATE_TIME_INPUT_MAX = "9999-12-31T23:59";

type DateInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { withTime?: boolean };

export default function DateInput({ withTime = false, max, ...props }: DateInputProps) {
  return (
    <input
      {...props}
      type={withTime ? "datetime-local" : "date"}
      max={max ?? (withTime ? DATE_TIME_INPUT_MAX : DATE_INPUT_MAX)}
    />
  );
}
