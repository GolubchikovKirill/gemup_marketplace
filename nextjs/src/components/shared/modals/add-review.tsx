import { Textarea } from "@/components/ui/textarea";

export const AddReview: React.FC = () => {
  return (
    <div className="hystmodal" id="addReview" aria-hidden="true">
      <div className="hystmodal__wrap">
        <div
          className="hystmodal__window baseModal"
          role="dialog"
          aria-modal="true"
        >
          <span data-hystclose className="ico-close"></span>
          <div className="form__data">
            <div className="form__header">
              <p className="title">Leave a Review</p>
            </div>
            <form action="" method="">
              <div className="form__fields">
                <div className="rating__wrapper">
                  <div className="head">Rate the product</div>
                  <div className="rate__wrapper">
                    <span className="value">0.0</span>
                    <div className="rating__stars" data-selected="0">
                      <i className="ico-star" data-value="1"></i>
                      <i className="ico-star" data-value="2"></i>
                      <i className="ico-star" data-value="3"></i>
                      <i className="ico-star" data-value="4"></i>
                      <i className="ico-star" data-value="5"></i>
                    </div>
                    <input type="hidden" name="rating" value="0" />
                  </div>
                </div>
                <Textarea name="" id="" placeholder="Enter the comment" />
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
