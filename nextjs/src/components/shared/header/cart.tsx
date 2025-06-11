import { useCartStore } from "@/store/cart";

export default function Cart() {
  const { isOpen, setIsOpen } = useCartStore((state) => state);
  
  return (
    <div className="cart__wrapper">
      <button className="cart" data-hystmodal="#cartModal" onClick={() => setIsOpen(true)}>
        <i className="ico-cart"></i>
        <div className="count__lable">
          <span>0</span>
        </div>
      </button>
    </div>
  );
}
