export const Pagination: React.FC = () => {
  return (
    <div className="pagination_wrapper">
        <div className="pagination">
            <a href="#"><span className="icon-arrow-left2"></span></a>
            <a href="#" className="active"><span>1</span></a>
            <a href="#"><span>2</span></a>
            <a href="#"><span>3</span></a>
            <a href="#"><span>4</span></a>
            <a href="#"><span className="icon-arrow-right2"></span></a>
        </div>
    </div>
  )
}
