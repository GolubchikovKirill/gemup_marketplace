import { InputPlacetop } from "../forms/input-placetop";

export const SendPass: React.FC = () => {
  return (
    <div className="hystmodal" id="forgotPassword" aria-hidden="true">
      <div className="hystmodal__wrap">
        <div
          className="hystmodal__window baseModal"
          role="dialog"
          aria-modal="true"
        >
          <span data-hystclose className="ico-close"></span>
          <div className="form__data">
            <div className="form__header">
              <p className="title">Reset password</p>
            </div>
            <form action="" method="">
              <div className="form__fields">
                <InputPlacetop id="reEmail" type="email" name="email" placeholder="" label="Email" required />
              </div>
              <div className="form__action">
                <button type="submit" disabled>
                  Send code
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
