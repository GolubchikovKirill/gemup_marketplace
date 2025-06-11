import type { ICommentItem } from "@/types/component";

export const CommentItem: React.FC<ICommentItem> = ({
    imgSrc = "",
    ico = "",
    name = "",
    subject = "",
    commentText = "",
    value = "",
    datetime = "",
}) => {
  return (
    <div className="comment__item">
      <div className="ava__wrapper">
        <img src={imgSrc} alt="name" />
        <i className={ico}></i>
      </div>
      <div className="comment__data">
        <span className="name">{name}</span>
        <span className="subject">{subject}</span>
        <div className="comment__body">
          <span className="title">Comment:</span>
          <p className="comment__text">{commentText}</p>
        </div>
      </div>
      <div className="comment__details">
        <div className="rating">
          <span className="value">{value}</span>
          <div className="stars__wrapper">
            <i className="ico-star active"></i>
            <i className="ico-star active"></i>
            <i className="ico-star active"></i>
            <i className="ico-star"></i>
            <i className="ico-star"></i>
          </div>
        </div>
        <div className="date">
          <span>{datetime}</span>
        </div>
      </div>
    </div>
  );
};
