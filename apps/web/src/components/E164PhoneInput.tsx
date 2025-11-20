import * as React from 'react';
import type { Country, Value as E164Number } from 'react-phone-number-input';
import { parsePhoneNumber } from 'react-phone-number-input';

import { PhoneInput } from '@/components/ui/phone-input';

type E164PhoneInputProps = Omit<
  React.ComponentProps<typeof PhoneInput>,
  'defaultCountry' | 'value' | 'onChange'
> & {
  value: E164Number | '';
  onChange: (value: E164Number | '') => void;
  fallbackCountry?: Country;
};

export function E164PhoneInput({
  value,
  onChange,
  fallbackCountry = 'US',
  ...rest
}: E164PhoneInputProps) {
  const [country, setCountry] = React.useState<Country>(fallbackCountry);

  React.useEffect(() => {
    if (!value) return;
    try {
      const parsed = parsePhoneNumber(value as string);
      if (parsed?.country) setCountry(parsed.country as Country);
    } catch {
      // ignore parsing errors and keep fallback country
    }
  }, [value, fallbackCountry]);

  return (
    <PhoneInput
      value={value}
      onChange={(v) => onChange(v || '')}
      defaultCountry={country}
      displayInitialValueAsLocalNumber
      {...rest}
    />
  );
}

export default E164PhoneInput;
