

export const UnverifiedBox: React.FC = () => {
  return (
    <section className="verify_acc">
      <div className="verifyAcc__message noVerify container">
        <div className="message__ico">
          <i className="ico-shield-close"></i>
        </div>
        <div className="message__data">
          <span className="title">Unverified Seller</span>
          <span className="subtext">
            To provide a feedback about the store, you must log in to your
            account
          </span>
        </div>
      </div>
    </section>
  );
};
