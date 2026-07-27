import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ru } from "../i18n/ru";
import type { BirthFormData, LocationSuggestion } from "../types";

interface FormScreenProps {
  initialData: BirthFormData;
  onSubmit: (data: BirthFormData) => void;
  searchLocations: (query: string, signal?: AbortSignal) => Promise<LocationSuggestion[]>;
}

type ValidationErrors = Partial<Record<"name" | "birthDate" | "birthTime" | "location", string>>;

const emptyLocationList: LocationSuggestion[] = [];

export function FormScreen({ initialData, onSubmit, searchLocations }: FormScreenProps) {
  const [data, setData] = useState(initialData);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [locations, setLocations] = useState<LocationSuggestion[]>(emptyLocationList);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const lastSelectedLabel = useRef(initialData.location?.label ?? "");

  const trimmedName = data.name.trim();
  const canSearch = data.locationQuery.trim().length >= 2 && !data.location;

  useEffect(() => {
    if (!canSearch) {
      setLocations(emptyLocationList);
      setIsSearching(false);
      setSearchError("");
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      setIsSearching(true);
      setSearchError("");
      searchLocations(data.locationQuery.trim(), controller.signal)
        .then((items) => {
          setLocations(items);
        })
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === "AbortError") {
            return;
          }
          setSearchError(ru.errors.generic);
          setLocations(emptyLocationList);
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setIsSearching(false);
          }
        });
    }, 350);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [canSearch, data.location, data.locationQuery, searchLocations]);

  const locationFeedback = useMemo(() => {
    if (searchError) {
      return searchError;
    }

    if (isSearching) {
      return ru.form.searching;
    }

    if (canSearch && locations.length === 0) {
      return ru.form.noLocations;
    }

    if (data.locationQuery.length > 0 && data.locationQuery.length < 2) {
      return "Введите минимум 2 символа.";
    }

    return "";
  }, [canSearch, data.locationQuery.length, isSearching, locations.length, searchError]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validate(data);
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length === 0) {
      onSubmit({
        ...data,
        name: trimmedName
      });
    }
  }

  function updateField<K extends keyof BirthFormData>(field: K, value: BirthFormData[K]) {
    setData((current) => ({
      ...current,
      [field]: value
    }));
    setErrors((current) => ({
      ...current,
      [field]: undefined
    }));
  }

  function updateLocationQuery(value: string) {
    setData((current) => ({
      ...current,
      locationQuery: value,
      location:
        current.location && value === lastSelectedLabel.current ? current.location : null
    }));
    setErrors((current) => ({
      ...current,
      location: undefined
    }));
  }

  function selectLocation(location: LocationSuggestion) {
    lastSelectedLabel.current = location.label;
    setData((current) => ({
      ...current,
      location,
      locationQuery: location.label
    }));
    setLocations(emptyLocationList);
    setErrors((current) => ({
      ...current,
      location: undefined
    }));
  }

  return (
    <section className="screen">
      <p className="eyebrow">{ru.brand}</p>
      <h1>{ru.form.title}</h1>
      <p className="muted">{ru.form.subtitle}</p>

      <form className="form-card" onSubmit={handleSubmit} noValidate>
        <label className="field">
          <span>{ru.form.name}</span>
          <input
            autoComplete="given-name"
            inputMode="text"
            maxLength={50}
            placeholder={ru.form.namePlaceholder}
            value={data.name}
            onChange={(event) => updateField("name", event.target.value)}
          />
          {errors.name ? <small className="field-error">{errors.name}</small> : null}
        </label>

        <div className="field-grid">
          <label className="field">
            <span>{ru.form.birthDate}</span>
            <input
              type="date"
              value={data.birthDate}
              onChange={(event) => updateField("birthDate", event.target.value)}
            />
            {errors.birthDate ? <small className="field-error">{errors.birthDate}</small> : null}
          </label>

          <label className="field">
            <span>{ru.form.birthTime}</span>
            <input
              type="time"
              value={data.birthTime}
              onChange={(event) => updateField("birthTime", event.target.value)}
            />
            {errors.birthTime ? <small className="field-error">{errors.birthTime}</small> : null}
          </label>
        </div>

        <p className="time-hint">{ru.form.timeHint}</p>

        <label className="field location-field">
          <span>{ru.form.birthPlace}</span>
          <input
            autoComplete="off"
            placeholder={ru.form.placePlaceholder}
            value={data.locationQuery}
            onChange={(event) => updateLocationQuery(event.target.value)}
          />
          {locations.length > 0 ? (
            <div className="location-list" role="listbox">
              {locations.map((location) => (
                <button
                  key={location.id}
                  type="button"
                  role="option"
                  className="location-option"
                  onClick={() => selectLocation(location)}
                >
                  <span>{location.label}</span>
                  {location.timezone ? <small>{location.timezone}</small> : null}
                </button>
              ))}
            </div>
          ) : null}
          {locationFeedback ? <small className="field-note">{locationFeedback}</small> : null}
          {errors.location ? <small className="field-error">{errors.location}</small> : null}
        </label>

        <div className="bottom-cta bottom-cta--inside">
          <button className="button button--primary" type="submit">
            {ru.form.continue}
          </button>
        </div>
      </form>
    </section>
  );
}

function validate(data: BirthFormData): ValidationErrors {
  const errors: ValidationErrors = {};
  const name = data.name.trim();

  if (name.length < 2 || name.length > 50) {
    errors.name = ru.errors.name;
  }

  if (!data.birthDate) {
    errors.birthDate = ru.errors.birthDate;
  }

  if (!data.birthTime) {
    errors.birthTime = ru.errors.birthTime;
  }

  if (
    !data.location ||
    !data.location.timezone ||
    data.location.latitude == null ||
    data.location.longitude == null ||
    !data.location.country
  ) {
    errors.location =
      data.locationQuery.trim().length >= 2 ? ru.form.chooseFromList : ru.errors.location;
  }

  return errors;
}
