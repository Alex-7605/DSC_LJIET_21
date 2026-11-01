"""Exercise all pages, filters, explicit training and a manual prediction."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

def test_all_pages_and_prediction():
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    assert not app.exception
    assert app.metric[0].value == "12,000"
    for page in ["Explore Data","Delivery Performance","Business Insights","Model Evaluation"]:
        app.radio(key="page").set_value(page).run()
        assert not app.exception, page
    buttons=[b for b in app.button if b.label=="Train and evaluate models"]
    buttons[0].click().run(timeout=60)
    assert not app.exception
    assert app.session_state["bundle"] is not None
    app.radio(key="page").set_value("Predict Delivery Risk").run()
    assert not app.exception
    next(b for b in app.button if b.label=="Estimate delivery risk").click().run()
    assert not app.exception
    assert any(m.label=="Estimated late risk" for m in app.metric)

def test_filters_change_metrics_and_empty_state():
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    region=next(m for m in app.multiselect if m.label=="Region")
    region.set_value(["SP"]).run()
    assert not app.exception
    assert int(app.metric[0].value.replace(",","")) < 12000
    category=next(m for m in app.multiselect if m.label=="Category")
    # A zero-length date window plus a rare category creates a stable empty combination.
    date_widget=app.date_input[0]
    first_day=date_widget.value[0]
    date_widget.set_value((first_day,first_day)).run()
    category=next(m for m in app.multiselect if m.label=="Category")
    category.set_value(["Unknown"]).run()
    assert not app.exception
    assert any("No orders match" in i.value for i in app.info)

def test_upload_selection_prompts_without_crashing():
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
    app.radio(key="data_choice").set_value("Upload CSV").run()
    assert not app.exception
    assert any("Choose a CSV" in i.value for i in app.info)