export interface IStoreMethod<T> {
    setValue: <K extends keyof Omit<T, "setValue">>(
        key: K,
        value: T[K]
    ) => void;
}