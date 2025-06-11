import Script from "next/script"

export const Scripts: React.FC = () => {
    return (
        <>
            {/* <Script src="/lib/js/swiper-bundle.min.js" />
            <Script src="/lib/js/venobox.min.js" />
            <Script src="/lib/js/hystmodal.min.js" />
            <Script src="/lib/js/slimselect.min.js" /> */}
            <Script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js" />
            <Script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js" />
        </>
    )
}