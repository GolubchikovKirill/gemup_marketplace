export interface IBaseError {
  error: boolean;
  message: string;
}

export interface IAuthError extends IBaseError {
  statusCode: number;
  timestamp: string;
  code: string;
  path: string;
}
