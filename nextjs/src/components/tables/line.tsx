interface ILineActive {
  active: boolean
  name: string
}

interface Props {
  active: boolean
  name: string
  amount: {
    sold: number
    total: number
  }
  date: string
  days: string
  shop: string,
  info: string
}



export const Line: React.FC<Props> = ({
  active,
  name = "",
  amount = {
    sold: 0,
    total: 0
  },
  date = "",
  days = "",
  shop = "",
  info = ""
}) => {
  return active
  ? <div className="element__line activated" data-category="All @@category">
      <div className="content__data">
        <span className="name">{name}</span>
        <span className="value green">{amount.sold} / {amount.total}</span>
        <span className="value green">{date} / {days}</span>
        <div className="actions">
          <button type="button">
            <i className="ico-cart"></i>
          </button>
          <a href="#" title="name">
            <i className="ico-eye"></i>
          </a>
        </div>
      </div>
      <div className="mainData">
        <span className="service">{info}</span>
        <span className="shop">{shop}</span>
      </div>
    </div>
  : <div className="element__line deactivated" data-category="All @@category">
  <div className="content__data">
    <span className="name">{name}</span>
    <span className="value green">{amount.sold} / <span className="er-red">Expired</span></span>
    <span className="value green">{date} / <span className="er-red">Expired</span></span>
    <div className="actions">
      <button type="button"><i className="ico-cart"></i></button>
    </div>
  </div>
  <div className="mainData">
    <span className="service">{info}</span>
    <span className="shop">{shop}</span>
  </div>
</div>
};
